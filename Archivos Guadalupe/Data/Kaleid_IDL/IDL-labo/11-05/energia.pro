pro energia

 spawn,'ls tek_p*_1105.dat',lista
 data=lista
 ;lista=[tek_p03_1105.dat tek_p04_1105.dat tek_p05_1105.dat tek_p06_1105.dat
 ;tek_p07_1105.dat tek_p08_1105.dat tek_p09_1105.dat tek_p10_1105.dat
 ;tek_p11_1105.dat tek_p12_1105.dat tek_p13_1105.dat tek_p14_1105.dat
 ;tek_pa16_1105.dat tek_pa17_1105.dat tek_pb16_1105.dat tek_pb17_1105.dat]


 ET=fltarr(n_elements(data))
 Dt= fltarr(n_elements(data))

 FOR N=0,n_elements(data)-1 DO BEGIN
 
  restore,filename=data(N)

  potencia=I_p * V_p

  P=tek_p(4,*) * tek_p(5,*)

  E= fltarr(n_elements(P)-1)

   for i=0,n_elements(E)-1  do  E(i)=P(i)* (t_p(i+1)-t_p(i))

  ET(N)=Total(E)
  Dt(N)=t_p(n_elements(E)-1)-t_p(0)

 ENDFOR

 
;stop
 
 header=strarr(3,1)
 header=['archivo,','Energia,','Dt']
 sEnergia= strarr(3,n_elements(ET))
 sEnergia[0,*] = data(*)+','
 sEnergia[1,*] = strtrim(ET,2)+',' 
 sEnergia[2,*] = strtrim(Dt,2)
 
 save ,data,ET,Dt, filename='Energia_pulsos_1105.dat'

openw,1,'Energia_pulsos_1105.txt'
;printf,1,'archivo - Energia y Dt'
printf,1,header
printf,1,sEnergia                
free_lun,1   

END
 


