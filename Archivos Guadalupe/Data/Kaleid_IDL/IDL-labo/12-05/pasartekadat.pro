pro pasartekadat ;, tek=tek, Rp=Rp
 ; leo y salvo t,ch1,ch2,Rm,I,V y Rp  para los cuales salve fueron
 ;paso algo en el media a parte de cambiar la Rp????
data=['tek0005ALL.csv','tek0006ALL.csv']

 a=[24,22,50,55,63,67]    ;tek05,06,08,09,11,12
 b=[990,990,800,800,810,810]
 Rpatron=[6000,2000]

restore,filename='guadatemplate.sav'

 FOR N=0 ,n_elements(data)-1 DO BEGIN

  tek=read_ascii(data(N),template=guada)
  Xi=a(N)
  Xf=b(N)
  Rp=Rpatron(N)
 
  Rm=(tek.Ch1(Xi:Xf)-tek.Ch2(Xi:Xf))*(Rp/tek.Ch2(Xi:Xf))
  V=tek.Ch1(Xi:Xf)-tek.Ch2(Xi:Xf)
  I=tek.Ch2(Xi:Xf)/Rp

  titulo=(strmid(data(N),0,7)+'ALL_1205')[0]

;stop
 ;set_plot,'X'
 ;window,1,xs=500,ys=450

 plot,tek.time(Xi:Xf),tek.Ch1(Xi:Xf),title= titulo, xtitle ='time(s)',$
 ytitle='Ch1,Ch2(volts)',background=16777215,color=0,/nodata
 oplot,tek.time(Xi:Xf),tek.Ch1(Xi:Xf),color=65535
 oplot,tek.time(Xi:Xf),tek.Ch2(Xi:Xf),color=16000000
 WRITE_JPEG, titulo +'.jpg', TVRD(/true), QUALITY=100,/true

 ;window,4,xsize=400,ysize=250
 ;plot,tek.time(Xi:Xf),Rm,xtitle='time(s)',ytitle='Rm(ohms)',$
 ;title='Resistencia_'+ titulo,background=16777215,color=0,/nodata
 ;oplot,tek.time(Xi:Xf),Rm,color=255
 ;WRITE_JPEG, 'Rm'+ titulo + '.jpg', TVRD(/true), QUALITY=100,/true

 ;window,5,xsize=400,ysize=250
 ;plot,tek.time(Xi:Xf),I,xtitle='time(s)',ytitle='I',$
 ;title='Corriente_'+ titulo,background=16777215,color=0,/nodata
 ;oplot,tek.time(Xi:Xf),I,color=50000
 ;WRITE_JPEG, 'I'+ titulo + '.jpg', TVRD(/true), QUALITY=100,/true

 window,2,xs=400,ys=250
 plot,V,I, xtitle='V(volts)', ytitle='I(amperes)',$
 title='I-V_'+ titulo,background=16777215,color=0,/nodata
 oplot,V,I,color=8005000
 WRITE_JPEG, 'I-V'+ titulo + '.jpg', TVRD(/true), QUALITY=100,/true

 window,3,xs=450,ys=250
 plot,I,Rm, xtitle='I(amperes)', ytitle='Rm(ohms)',$
 title='Rm-I_'+ titulo,background=16777215,color=0,/nodata
 oplot,I,Rm,color=255
 WRITE_JPEG, 'Rm-I'+ titulo + '.jpg', TVRD(/true), QUALITY=100,/true

 window,6,xs=450,ys=250
 plot,I,Rm, xtitle='I(amperes)', ytitle='Rm(ohms)',$
 title='Rm-I_'+ titulo,background=16777215,color=0,/nodata
 oplot,I,Rm,color=255,psym=1
 WRITE_JPEG, 'Rm-I'+ titulo + 'sim.jpg', TVRD(/true), QUALITY=100,/true
;stop
 t=tek.time(Xi:Xf)  
 Ch1=tek.Ch1(Xi:Xf)
 Ch2=tek.Ch2(Xi:Xf)
 ;Rm_p=Rm
 ;I_p=I
 ;V_p=V
 save,t,Ch1,Ch2,Rm,I,V,Xi,Xf,Rp,filename= titulo +'.dat'
 
 ENDFOR

end


