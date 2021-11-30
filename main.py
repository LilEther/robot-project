# Librairie
from micropython import const
from machine import *
from DRV8833 import *
from VL6180X import *
from BME280 import *
import pycom
import time
import os

# ---------- Moteur

#Variables globales pour moteurs
DRV8833_Sleep_pin = 'P20' # Pin SLEEP
DRV8833_AIN1 = 'P22' # Entrée PWM moteur A : AIN1
DRV8833_AIN2 = 'P21' # Entrée PWM moteur A : AIN2
DRV8833_BIN1 = 'P19' # Entrée PWM moteur B : BIN1
DRV8833_BIN2 = 'P12' # Entrée PWM moteur B : BIN2

# Vitesse de rotation des roues
V = 50

# Routines de déplacements du robot
def Avancer(vitesse):
    Moteur_Droit.Cmde_moteur(SENS_HORAIRE, vitesse-25)
    Moteur_Gauche.Cmde_moteur(SENS_ANTI_HORAIRE, vitesse)
def Reculer(vitesse):
    Moteur_Droit.Cmde_moteur(SENS_ANTI_HORAIRE, vitesse)
    Moteur_Gauche.Cmde_moteur(SENS_HORAIRE, vitesse)
def Pivoter_droite(vitesse):
    Moteur_Droit.Cmde_moteur(SENS_ANTI_HORAIRE, vitesse)
    Moteur_Gauche.Cmde_moteur(SENS_ANTI_HORAIRE, vitesse)
def Pivoter_gauche(vitesse):
    Moteur_Droit.Cmde_moteur(SENS_HORAIRE, vitesse)
    Moteur_Gauche.Cmde_moteur(SENS_HORAIRE, vitesse)
def Arret():
    Moteur_Droit.Cmde_moteur(SENS_HORAIRE, 0)
    Moteur_Gauche.Cmde_moteur(SENS_HORAIRE, 0)

# Initialisation des moteurs
Moteur_Gauche = DRV8833(DRV8833_AIN1, DRV8833_AIN2, DRV8833_Sleep_pin, 1, 500, 0, 1) # Sur connecteur Encoder1
Moteur_Droit = DRV8833(DRV8833_BIN1, DRV8833_BIN2, DRV8833_Sleep_pin, 1, 500, 2, 3) # Sur connecteur Encoder2
Arret()

#Init I2C
bus_i2c = I2C()
bus_i2c.init(I2C.MASTER, baudrate = 400000)
adr = bus_i2c.scan()

# ---------- Capteur humi/temp/pres

#Initialisation  et valibrage du capteur humi/temp/pres
Id_BME280 = bus_i2c.readfrom_mem(BME280_I2C_ADR,BME280_CHIP_ID_ADDR, 1)
capteur_BME280 = BME280 (BME280_I2C_ADR, bus_i2c)
capteur_BME280.Calibration_Param_Load()
print("L'adresse du périphérique I2C est :",adr)
print ('Valeur ID BME280 :', hex (Id_BME280[0]))

# ---------- Capteur de lumi et distances

# Variables globales pour les 2 capteurs
Distance = [-1, -1]
Luminosite = [-1.0, -1.0]

# Nombre de capteurs utilises
N_VL6180X = const(2)

#Variables globales pour capteurs
VL6180X_CE_Pin = ('P3', 'P5')

# adresse i2c par defaut 0x29 soit 41
VL6180X_I2C_adr_defaut = const(0x29)

# Plage d'adressage I2C des 3 capteurs VL6180X
VL6180X_I2C_Adr = (const(0x2A), const(0x2B))

# Liste des variables Pin correspondant aux broches
VL6180X_GPIO_CE_Pin = []
for pin in VL6180X_CE_Pin :
    VL6180X_GPIO_CE_Pin.append(Pin(pin, mode=Pin.OUT))
    VL6180X_GPIO_CE_Pin[-1].value(0)

# liste des capteurs de distance : vide a l'initialisation
capteur_VL6180X = []
for i in range (N_VL6180X):
    VL6180X_GPIO_CE_Pin[i].value(1)
    time.sleep(0.002)
    capteur_VL6180X.append(VL6180X(VL6180X_I2C_adr_defaut, bus_i2c))
    capteur_VL6180X[i].Modif_Adr_I2C(VL6180X_GPIO_CE_Pin[i],VL6180X_I2C_Adr[i], VL6180X_I2C_adr_defaut)

adr = bus_i2c.scan()
print ('Adresse peripherique I2C (2) :', adr)

# ---------- Gestion des données dans la carte SD

#Variable global pour le capteur
save = True
try:
    sd = SD()
    os.mount(sd, '/sd')
    # ouverture en ecriture : 'w'
    with open('/sd/data.csv','w') as f:
        f.write('Index;Temperature;Humidite;Pression\r\n')
except OSError:
    save = False

# ---------- Boucle principale

Index = 1
while True :
    #Lire les informations
    temp = capteur_BME280.read_temp()
    humi = capteur_BME280.read_humidity()
    pres = capteur_BME280.read_pression()

    print("-------------------------------------------------------------------")
    print(Index)
    print("Température :","%.2f"%temp,"- Humidité :","%.2f"%humi,"- Préssion :","%.2f"%pres)

    #Enregistrer les datas des capteur et la position
    if save == True:
        with open('/sd/data.csv','a') as f:
            f.write(str(Index))
            f.write(";")
            f.write("%.2f"%temp)
            f.write(";")
            f.write("%.2f"%humi)
            f.write(";")
            f.write("%.2f"%pres)
            f.write("\r\n")

    #Boucle de 4s
    I = 0
    for e in range(20):
        print(I+1,"--------------")
        #Lire les infos distance
        for i in range (N_VL6180X) :
            Distance[i] = capteur_VL6180X[i].range_mesure ()
            Luminosite[i] = capteur_VL6180X[i].ambiant_light_mesure ()

        print ('Distance : %d %d' %(Distance[0], Distance[1]))
        print ('Luminosite : %.1f %.1f' %(Luminosite[0],Luminosite[1]))

        print('-> Démarage')
        if Distance[0] <= 60:
            Reculer(V)
            time.sleep(0.20)
            Pivoter_droite(V)
            time.sleep(0.20)

        Avancer(V)
        time.sleep(0.20)

        print('-> Arret')
        Arret()
        I += 1

    Index +=1
