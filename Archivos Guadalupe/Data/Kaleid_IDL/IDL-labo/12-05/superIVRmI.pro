pro superIVRmI


 data=['tek0005ALL_1205.dat','tek0006ALL_1205.dat']
 COLORES=[250,16000000]
 restore,data(0)
 titulo='tek005-tek006_1205'

 window,2,xs=450,ys=250
 plot,I,Rm, xtitle='I(amperes)', ytitle='Rm(ohms)',yrange=[-2000,10000],$
 xrange=[0,.0085],title='Rm-I_'+ titulo,background=16777215,color=0,/nodata

 FOR N=0,1 DO BEGIN
  restore,data(N) 
  oplot,I,Rm,color=COLORES(N),psym=4
 ENDFOR

  WRITE_JPEG, 'Rm-I'+ titulo + '.jpeg', TVRD(/true), QUALITY=100,/true

window,3,xs=400,ys=250
 plot,V,I, xtitle='V(volts)', ytitle='I(amperes)',yrange=[0,.0085],$
 title='I-V_'+ titulo,background=16777215,color=0,/nodata

FOR N=0,1 DO BEGIN
  restore,data(N) 
  oplot,V,I,color=COLORES(N)
 ENDFOR

  WRITE_JPEG, 'I-V'+ titulo + '.jpeg', TVRD(/true), QUALITY=100,/true
stop

END
