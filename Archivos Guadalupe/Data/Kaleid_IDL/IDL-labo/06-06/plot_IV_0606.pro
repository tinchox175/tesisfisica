PRO plot_IV_0606

;xxxxxxxxxxxxxxxxxxxxxxVERVERVEVR
;--------------grafica
;---------Rm-I de tek 01-02-04-05 del 0606

  ;;;;;; lee todas las rampas y las grafica o todas las piramides truncadas 
  ;;;;;; lee todas los plateau y las grafica o todos los picos

  ;spawn,'ls tek_*01_0606.dat',lista   ;;; tek 01 rampa,pt,pi,p
  ;spawn,'ls tek_*02_0606.dat',lista  ;;;
  ;spawn,'ls tek_*04_0606.dat',lista  ;;; 
  spawn,'ls tek_*05_0606.dat',lista  ;;; 
  ;lista=[]

 FOR I=0,n_elements(lista)-1  DO restore,lista(I)
 ;titulo='IV_tek01_0606'
 ;titulo='IV_tek02_0606'
 ;titulo='IV_tek04_0606'
 titulo='IV_tek05_0606'

 set_plot,'X'
 ;window,1,xs=400,ys=250
 window,1
 plot,V_pi,I_pi,title=titulo,ytitle='!3I(amperes)',xtitle='V(volts)',$
 yrange=[0,.012],xrange=[-1,10],xstyle=1,background=16777215,color=0,/nodata

 Color= [255,8005000,16000000,655355,16500000,18500000];2005000

 oplot,V_r,I_r,color=Color(0);,psym=3,symsize=0.5
 oplot,V_pt,I_pt,color=Color(1),psym=1,symsize=0.5
 oplot,V_pt,I_pt,color=Color(1)
 oplot,V_pi,I_pi,color=Color(2),psym=5,symsize=1
 oplot,V_pi,I_pi,color=Color(2)

 XYOUTS,100,300,'-',color=Color(0),/device
 XYOUTS,120,300,'rampa', color=0,/device

 XYOUTS,200,300,'+',color=Color(1),/device
 XYOUTS,220,300,'pt',color=0,/device
 
  PLOTS,300,303,psym=5,color=Color(2),/device
  XYOUTS,310,300,'pi',color=0,/device
 
 
 WRITE_JPEG,titulo, TVRD(/true), QUALITY=100,/true


END
