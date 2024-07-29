 PRO energia

 spawn,'ls tek_p*_1205.dat',lista
 data=lista

  ;data=['tek_p05_1205.dat','tek_p06_1205.dat','tek_p08_1205.dat','tek_p09_1205.dat',$
  ;'tek_p11_1205.dat','tek_p12_1205.dat','tek_pa02_1205.dat','tek_pa03_1205.dat',$
  ;'tek_pa04_1205.dat','tek_pa10_1205.dat','tek_pa13_1205.dat','tek_pa14_1205.dat',$
  ;'tek_pa15_1205.dat','tek_pa16_1205.dat','tek_pa17_1205.dat','tek_pb02_1205.dat',$
  ;'tek_pb03_1205.dat','tek_pb04_1205.dat','tek_pb10_1205.dat','tek_pb13_1205.dat',$
  ;'tek_pb14_1205.dat','tek_pb15_1205.dat','tek_pb16_1205.dat','tek_pb17_1205.dat',$
  ;'tek_pc02_1205.dat','tek_pc03_1205.dat','tek_pc04_1205.dat','tek_pc14_1205.dat',$
  ;'tek_pc15_1205.dat','tek_pc16_1205.dat','tek_pc17_1205.dat','tek_pd03_1205.dat',$
  ;'tek_pd04_1205.dat','tek_pd15_1205.dat','tek_pd16_1205.dat','tek_pd17_1205.dat',$
  ;'tek_pe16_1205.dat','tek_pe17_1205.dat','tek_pf17_1205.dat']


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

 Energia= fltarr(2,n_elements(ET))
 Energia[0,*] = ET
 Energia[1,*] = Dt
;stop
 sEnergia=strtrim(Energia,2)

 sEnergia[0,*] =sEnergia[0,*]+',' 
 
 save , ET,Dt, filename='Energia_pulsos_1205.dat'

openw,1,'Energia_pulsos_1205.txt'
printf,1,'Energia y Dt'
printf,1,sEnergia                
free_lun,1   


END



