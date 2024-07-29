pro leercsv  , dat=dat, Xi=Xi,Xf=Xf,Rp=Rp
 ; leo y salvo t,ch1,ch2,Rm,I,V y Xi,Xf,Rp 
 

restore,filename='guadatemplate.sav'

  tek=read_ascii(dat,template=guada)
 
 
  Rm=(tek.Ch1(Xi:Xf)-tek.Ch2(Xi:Xf))*(Rp/tek.Ch2(Xi:Xf))
  V=tek.Ch1(Xi:Xf)-tek.Ch2(Xi:Xf)
  I=tek.Ch2(Xi:Xf)/Rp

  titulo=(strmid(dat,0,7)+'rp1_1205')[0]

;stop
 set_plot,'X'
 window,1,xs=500,ys=450

 plot,tek.time(Xi:Xf),tek.Ch1(Xi:Xf),title= titulo, xtitle ='time(s)',$
 ytitle='Ch1,Ch2(volts)',background=16777215,color=0,/nodata
 oplot,tek.time(Xi:Xf),tek.Ch1(Xi:Xf),color=65535
 oplot,tek.time(Xi:Xf),tek.Ch2(Xi:Xf),color=16000000
 WRITE_JPEG, titulo +'.jpg', TVRD(/true), QUALITY=100,/true

 window,4,xsize=400,ysize=250
 plot,tek.time(Xi:Xf),Rm,xtitle='time(s)',ytitle='Rm(ohms)',$
 title='Resistencia_'+ titulo,background=16777215,color=0,/nodata
 oplot,tek.time(Xi:Xf),Rm,color=255
 WRITE_JPEG, 'Rm'+ titulo + '.jpg', TVRD(/true), QUALITY=100,/true

 window,5,xsize=400,ysize=250
 plot,tek.time(Xi:Xf),I,xtitle='time(s)',ytitle='I',$
 title='Corriente_'+ titulo,background=16777215,color=0,/nodata
 oplot,tek.time(Xi:Xf),I,color=50000
 WRITE_JPEG, 'I'+ titulo + '.jpg', TVRD(/true), QUALITY=100,/true

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
 
 

end


