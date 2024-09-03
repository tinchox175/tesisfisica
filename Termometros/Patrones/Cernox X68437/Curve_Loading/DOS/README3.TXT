MODEL 8000 OPTION
DISK STORAGE OF SENSOR CALIBRATION DATA
FILE DESCRIPTION:  TEXT DOCUMENT FORMAT


The Model 8000 consists of disk storage of calibration
data for the Lake Shore Cryotronics, Inc. temperature
sensors. For each sensor there are three calibration files
containing the test data, the coefficients for a data fit,
and an interpolation table. There are also instrument files
containing the necessary data to insert the calibration
directly into a Lake Shore instrument using LSCurves.exe
which is also included on this disk. The exact combination
of files contained on this disk depends upon the temperature
sensor type and model. The following table lists the files
included for each sensor type. A description of each file
type follows.

IMPORTANT NOTE:
While the accuracy of the calibration is at best on the
order of several millikelvin, all test data are reported to
double precision within the electronic files to allow the
user to duplicate the curve fitting and numerical results
performed by Lake Shore. This DOES NOT imply that the
accuracy or resolution is measured to fifteen digits.


 Sensor Type        Calibration Files        Instrument Files
=============    ========================    ================
Cernox           Test data list                    91C
Germanium        Chebychev polynomial fit          34A
Carbon Glass     Interpolation Table               330
Thermox                                            340
Rox                                                234
-------------    ------------------------    ------------------
Platinum         Test data list                    91C
Rhodium-Iron     Chebychev polynomial fit          34A
                 Interpolation Table               330
                                                   340
-------------    ------------------------    ------------------
Silicon Diode    Test data list                    91C
                 Chebychev polynomial fit          34A
                 Interpolation Table               330
                                                   340
-------------    ------------------------    ------------------
GaAlAs Diode     Test data list                    91C
                 Cubic Spline Data fit             34A
                 Interpolation Table               330
                                                   340
-------------    ------------------------    ------------------

CALIBRATION FILE DESCRIPTIONS

All these files are in ASCII format, where SerialNumber is the
serial number of the sensor.

--------------------------------------------
The test data file (SerialNumber.DAT):

This file contains measurements of resistance or voltage
and the corresponding temperatures.

The format for resistors is:

==============
Temperature (K)        Resistance (ohms)

D.DDDDDDDDDDDDDDESYY   D.DDDDDDDDDDDDDDESYY
D.DDDDDDDDDDDDDDESYY   D.DDDDDDDDDDDDDDESYY
D.DDDDDDDDDDDDDDESYY   D.DDDDDDDDDDDDDDESYY
     .                       .
     .                       .
     .                       .
==============

The format for diodes is:

==============
Temperature (K)        Voltage (volts)

D.DDDDDDDDDDDDDDESYY   D.DDDDDDD
D.DDDDDDDDDDDDDDESYY   D.DDDDDDD
     .                     .
     .                     .
     .                     .
==============

where  "D" is a numeric digit
       "." is the decimal point
       "E" indicates exponential format
       "S" indicates the sign of the exponent ("+" or "-") and
       "YY" a two digit exponent.

       There are three spaces between the two numbers.

--------------------------------------------
The coefficient file (SerialNumber.COF):

This file contains the Chebychev polynomial coefficients for a
curve fit allowing the user to transform sensor voltage or
resistance measurements into their equivalent temperature.
Consult the Calibration Report Description for information
regarding converting resistances or voltages to temperature
using the Chebychev polynomial and coefficients. The electronic
file contains a label for each entry identifying it use for
the fit. Standard fits are performed either as temperature versus
voltage (diodes), temperature versus resistance, or temperature
versus LOG10(resistance) depending upon the shape of the
characteristic as a function of temperature.

The following is an example coefficient file for a platinum
sensor:

==============
Number of fit ranges:           2
Fit range:                      1
Fit type for range:             LOG
Order of fit range 1:           9
Zlower for fit range 1:        -5.20725516305026E-01
Zupper for fit range 1:         1.61631713297016E+00
Lower limit for fit range 1:    0.4289
Upper limit for fit range 1:    32.8444
C(0) Equation 1:                5.35472104488059E+01
C(1) Equation 1:                4.84343274320430E+01 
C(2) Equation 1:                1.78731249180996E+01 
C(3) Equation 1:                6.71910632694103E+00 
C(4) Equation 1:                2.24957224549801E+00 
C(5) Equation 1:                6.83864572708680E-01
C(6) Equation 1:                1.64705729725070E-01 
C(7) Equation 1:                2.77035831899347E-02 
C(8) Equation 1:                8.54503010777701E-04 
C(9) Equation 1:               -3.20164326544564E-03 
FIT RANGE:                      2
Fit type for range 2:           LIN
Order of fit range 2:           5
Zlower for fit range 2:         2.632490364723370E+01
Zupper for fit range 2:         1.280000000000000E+02
Lower limit for fit range 2:    32.8444
Upper limit for fit range 2:    124.4599
C(0) Equation 1:                2.178061368696580E+02 
C(1) Equation 1:                1.248272296845860E+02 
C(2) Equation 1:                1.516717512664060E+00 
C(3) Equation 1:               -0.123110200579409E-01 
C(4) Equation 1:                3.970264241545280E-02 
C(5) Equation 1:               -1.341884049509500E-03 
==============


The calibration report for each sensor and the accompanying
sheet "Calibration Report Description" give a complete
description of these parameters and how to use them.

--------------------------------------------
The interpolation table file (SerialNumber.TBL):

A table yielding resistance or voltage at predefined
temperatures is generated using a cubic spline curve fitting
routine. In this file, each data record consists of a
temperature in Kelvin, the corresponding resistance in Ohms
(for resistors) or Voltage (for diodes) in volts, the
corresponding sensitivity (dR/dT or dV/dT) in ohms/kelvin
(for resistors) or millivolts/kelvin (for diodes). Additionally,
the dimensionless sensitivity Sd=(T/R)(dR/dT)=d(logR)/d(logT)
is included for resistors.

The format for resistors is:

==============
Temp      Resistance               Sensitivity    Dimensionless
(K)       (ohms)                   (ohms/kelvin)  Sensitivity

DDD.DDD   SD.DDDDDDDDDDDDDDDESYY   SD.DDDDDESYY   SD.DDDDESYY
DDD.DDD   SD.DDDDDDDDDDDDDDDESYY   SD.DDDDDESYY   SD.DDDDESYY
DDD.DDD   SD.DDDDDDDDDDDDDDDESYY   SD.DDDDDESYY   SD.DDDDESYY
   .             .                    .                    .
   .             .                    .                    .
   .             .                    .                    .
==============

The format for resistors is:

==============
Temp      Voltage     Sensitivity
(K)       (volts)     (millivolts/kelvin)

DDD.DDD   D.DDDDDDD   SDDDD.DDDDDESYY 
DDD.DDD   D.DDDDDDD   SDDDD.DDDDDESYY 
DDD.DDD   D.DDDDDDD   SDDDD.DDDDDESYY 
   .         .              .
   .         .              .
   .         .              .
==============

where   "D" is a numeric digit
        "." is the decimal point
        "E" indicates exponential format
        "S" indicates the sign of the exponent
            ("-" or blank for "+") and
        "YY" a two digit exponent.

        There are three spaces between the numbers.

--------------------------------------------
The cubic Spline file (SerialNumber.SPL):

Each data record contains a
temperature in Kelvin and the corresponding resistance in
ohms or voltage (for diodes), and the curvature in the
following format:

The format for resistors is:

==============
Temperature            Resistance             Curvature
(Kelvin)               (Ohms)                 (Kelvin/ohm/ohm)

D.DDDDDDDDDDDDDDESYY   D.DDDDDDDDDDDDDDESYY   SD.DDDDDDDDDDDDDDESYY
D.DDDDDDDDDDDDDDESYY   D.DDDDDDDDDDDDDDESYY   SD.DDDDDDDDDDDDDDESYY
D.DDDDDDDDDDDDDDESYY   D.DDDDDDDDDDDDDDESYY   SD.DDDDDDDDDDDDDDESYY
      .                       .                        .
      .                       .                        .
      .                       .
==============         

The format for diodes is:

==============
Temperature            Voltage     Curvature
(Kelvin)               (Volts)     (Kelvin/Volt/Volt)

D.DDDDDDDDDDDDDDESYY   D.DDDDDDD   SD.DDDDDDDDDDDDDDESYY
D.DDDDDDDDDDDDDDESYY   D.DDDDDDD   SD.DDDDDDDDDDDDDDESYY
D.DDDDDDDDDDDDDDESYY   D.DDDDDDD   SD.DDDDDDDDDDDDDDESYY
      .                     .              .
      .                     .              .
      .                     .              .
==============

where  "D" is a numeric digit
       "." is the decimal point
       "E" indicates exponential format
       "S" indicates the sign of the exponent ("+" or "-") and
       "YY" a two digit exponent.

       There are three spaces between the two numbers.


CALCURVE FILE DESCRIPTIONS FOR USE WITH LSCI INSTRUMENTS
-----------------------------------------------------------
The 330 CalCurve file (SerialNumber.330):

The .330 file is a readable listing of the temperature-sensor
units pairs to be programmed into a Lake Shore instrument
such as the Model 330, 91C or 93C. The following is an
example of this file.

==============
Sensor Model:    MODEL        
Serial Number:   SerialNumber    
Interpolation Method:  Straight Line
SetPoint Limit:  325  (Kelvin)
Data Format:     2  (Volts/Kelvin)
Number of BreakPoints:  81

No.  Units    Temperature (K)

 1  0.82640     325.0
 2  0.85510     315.0
 3  0.92646     290.0
 4  0.95472     280.0
 .     .         .
 .     .         .
 .     .         .
==============

-----------------------------------------------------------
The 91C CalCurve file (SerialNumber.91C):

The 91C file is the actual temperature-sensor units
data string to be programmed into a Lake Shore instrument
such as the Model 330, 91C, or 93C. The following is an
example of the 91C format (note:  hard returns have been
added for clarity; this is normally a one line character
string):

==============
XC06,S00MODELXXXXXX,
0.09032,475.0,0.12536,460.0,0.18696,435.0,0.29959,390.0,
0.42238,340.0,0.45613,325.0,0.49252,310.0,0.54084,290.0,
0.58890,270.0,0.63669,250.0,0.67228,235.0,0.70762,220.0,
0.74266,205.0,0.77736,190.0,0.80028,180.0,0.82303,170.0,
0.84557,160.0,0.85675,155.0,0.86789,150.0,0.87896,145.0,
0.88996,140.0,0.90089,135.0,0.91175,130.0,0.92252,125.0,
0.93321,120.0,0.94380,115.0,0.95431,110.0,0.96471,105.0,
0.97500,100.0,0.98516,095.0,0.99519,090.0,1.00509,085.0,
1.01483,080.0,1.02443,075.0,1.03387,070.0,1.04316,065.0,
1.05231,060.0,1.05954,056.0,1.07019,050.0,1.08402,042.0,
1.08919,039.0,1.09274,037.0,1.09641,035.0,1.09832,034.0,
1.10028,033.0,1.10232,032.0,1.10446,031.0,1.10674,030.0,
1.10918,029.0,1.11187,028.0,1.11494,027.0,1.11870,026.0,
1.12423,025.0,1.13510,024.0,1.15427,023.0,1.17550,022.0,
1.19466,021.0,1.22977,019.0,1.25575,017.5,1.28303,016.0,
1.31194,014.5,1.34351,013.0,1.36678,012.0,1.39194,011.0,
1.41972,010.0,1.45075,009.0,1.48553,008.0,1.52378,007.0,
1.59564,005.2,1.63287,004.2,1.65973,003.4,1.68045,002.7,
1.69299,002.2,1.70105,001.8,1.70570,001.5,1.70697,001.4*
==============

-----------------------------------------------------------
The 340 CalCurve files (SerialNumber.340) and
(SerialNumber.34A):

The .34A file is a data file to be programmed into a Lake
Shore instrument such as the Model 340 or 218. The .340 file
is a readable listing of the information contained in the
.34A file. An example of the 340 format:

==============
Sensor Model:   SensorModel
Serial Number:  SerialNumber
Data Format:    2      (Volts/Kelvin)
SetPoint Limit: 325.      (Kelvin)
Temperature coefficient:  1 (Negative)
Number of Breakpoints:   28

No.   Units      Temperature (K)

  1  .464429       325.000
  2  .507562       307.000
  3  .552900       288.000
  4  .600367       268.000
  .     .            .
  .     .            .
  .     .            .
==============

An example of the 34A format:

==============
Name: SensorModel
Serial number: SerialNumber
Format: 4             ; Log Ohms/Kelvin
Limit: 100.00
Coefficient: 1        ; Negative
Point 1: 1.87808,100.0
Point 2: 1.88572,97.0
Point 3: 1.89222,94.5
Point 4: 1.89886,92.0
Point 5: 1.90566,89.5
   .        .
   .        .
   .        .
==============

-----------------------------------------------------------
The 234 CalCurve files (SerialNumber.234):

The .234 file is a data file with resistance/temperature
points formatted for the LSCI Model 234 transmitter.
The first entry in the file is the sensor serial number.
Each subsequent data record consists of LOG10(resistance)
- temperature data pairs. An example of the 234 format:

==============
SerialNumber
0.00,325.000
0.02,325.000
0.04,325.000
0.60, 44.422
0.62, 43.194
 .      .
 .      .
 .      . 
==============


-----------------------------------------------------------
All CalCurve Files can be loaded into the appropriate instrument
using the provided LSCURVES software. Please see lscurves.txt
for more details regarding using the software.