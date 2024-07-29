PRO plot_RmI_0606

;xxxxxxxxxxxxxxxxxxxxxxVERVERVEVR
;--------------grafica
;---------Rm-I de tek 01-02-04-05 del 0606

  ;;;;;; lee todas las rampas y las grafica o todas las piramides truncadas 
  ;;;;;; lee todas los plateau y las grafica o todos los picos

  spawn,'ls tek_*01_0606.dat',lista   ;;; tek 01 rampa,pt,pi,p
  ;spawn,'ls tek_*02_0606.dat',lista  ;;;
  ;spawn,'ls tek_*04_0606.dat',lista  ;;; 
  ;spawn,'ls tek_*05_0606.dat',lista  ;;; 
  ;lista=[]

 FOR I=0,n_elements(lista)-1  DO restore,lista(I)
 titulo='RmI_tek01_0606'
 ;titulo='RmI_tek02_0606'
 ;titulo='RmI_tek04_0606'
 ;titulo='RmI_tek05_0606'

 set_plot,'X'
 ;window,1,xs=400,ys=250
 window,1
 plot,I_pi,Rm_pi,title=titulo,xtitle='!3I(amperes)',ytitle='Rm(!4X!3)',$
 yrange=[0,6000],xrange=[0,0.002],background=16777215,color=0,/nodata
 
 Color= [255,8005000,16000000,655355,16500000,18500000];2005000

 oplot,I_r,Rm_r,color=Color(0);,psym=3,symsize=0.5
 oplot,I_pt,Rm_pt,color=Color(1),psym=1,symsize=0.5
 oplot,I_pt,Rm_pt,color=Color(1)
 oplot,I_pi,Rm_pi,color=Color(2),psym=5,symsize=1
 oplot,I_pi,Rm_pi,color=Color(2)

 XYOUTS,100,300,'-',color=Color(0),/device
 XYOUTS,120,300,'rampa', color=0,/device

 XYOUTS,200,300,'+',color=Color(1),/device
 XYOUTS,220,300,'pt',color=0,/device
 
  PLOTS,300,303,psym=5,color=Color(2),/device
  XYOUTS,310,300,'pi',color=0,/device
 
 
;stop
 WRITE_JPEG,titulo, TVRD(/true), QUALITY=100,/true




 ;num=[2,3,4,10,13,14,15,16,17]
 ;spawn,'ls tek_p*_1205.dat',listap
 ;data=listap[6:*]

;stop
 ;;window,2,xs=400,ys=250
 ;;plot,I,Rm,title=titulo,xtitle='!3I(amperes)',ytitle='Rm(!4X!3)',$
; ;yrange=[0,10000],xrange=[0,0.02],background=16777215,color=0,/nodata

 ;FOR M=0, n_elements(data)-1 do begin
   ;nume=string(M)
; restore,data(M)
 ;oplot,V,I,color=0,psym=2,symsize=0.2
 ;XYOUTS,100,215,'**',color=0,/device
 ;XYOUTS,120,215,'tek_p2-17',color=0,/device
 ;ENDFOR
; fila='IV_superp-5-6-8-9-11-12+p 2-3-4-10-13-14-15-16-17'
 ;WRITE_JPEG,fila, TVRD(/true), QUALITY=100,/true
 

END
