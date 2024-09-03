'TGPLINE.BAS evaluates temperature of a device from the data
'            contained in the SPL file.
'
DEFDBL A-Z
OPTION BASE 1
CLS
INPUT "Enter sensor serial number: ", sernum$
PRINT
OPEN sernum$ + ".SPL" FOR INPUT AS #1
INPUT #1, n%                           'Read number of data points from file.
DIM t(n%), v(n%), C(n%), S(0 TO 3)     'Dimension the necessary vectors.
FOR i% = 1 TO n%
  INPUT #1, t(i%), v(i%), C(i%)       'Read data from file. C() is curvature.
NEXT i%
CLOSE #1
DO
  volts$ = ""
  LINE INPUT "Enter voltage: ", volts$
  IF volts$ = "" THEN EXIT DO         'End if Enter is pressed without value.
  voltage = VAL(volts$)
  IF voltage <= v(1) AND voltage >= v(n%) THEN  'Make sure value is in range.
    FOR k% = 1 TO n% - 1
      IF v(k%) < voltage THEN EXIT FOR                 'Find proper interval.
    NEXT k%
    IF k% = n% THEN k% = k% - 1       'Will only happen if voltage <= v(n%-1)
    dv = v(k% + 1) - v(k%)
    dt = t(k% + 1) - t(k%)
    dx = voltage - v(k%)
    S(0) = t(k%)          'Callculate coefficients for cubic spline equation.
    S(1) = dt / dv - dv * (2# * C(k%) + C(k% + 1)) / 6#
    S(2) = C(k%) / 2#
    S(3) = (C(k% + 1) - C(k%)) / (6# * dv)
    temperature = S(0) + S(1) * dx + S(2) * dx * dx + S(3) * dx * dx * dx
    dTdV = S(1) + 2# * S(2) * dx + 3# * S(3) * dx * dx   'Compute derivative.
    dVdT = 1# / dTdV         'Sensitivity is reciprocal of spline derivative.
    PRINT "For V = ";
    PRINT USING "#.######"; voltage;     'Print out voltage, temperature, and
    PRINT ", T = ";                      'sensitivity, scaling sensitivity to
    PRINT USING "###.####"; temperature; 'mV/K instead of V/K.
    PRINT " K, and dV/dT = ";
    PRINT USING "#####.###"; 1000# / dTdV;
    PRINT " mV/K"
    PRINT
  ELSE                       'Error message if value entered is out of range.
    BEEP
    PRINT
    PRINT "Value entered is out of the range of the calibration data."
    PRINT
  END IF
LOOP

