PRO plot_IV_todas

;--------------grafica I-V 
;---------Rm-I de tek 01-02-04-05 del 0606

  ;;;;;; lee todas las rampas y las grafica o todas las piramides truncadas 
  ;;;;;; lee todas los plateau y las grafica o todos los picos

 ;spawn,'ls tek_r*_0606.dat',lista   ;;; la rampa
 ;spawn,'ls tek_pt*_0606.dat',lista  ;;; la piramide truncada
 ;spawn,'ls tek_p0*_0606.dat',lista  ;;; el plateau
  spawn,'ls tek_pi*_0606.dat',lista  ;;; el pico
  ;lista=[]

 restore,lista(0)
	;Rm=Rm_r
	;I=I_r
	;V=V_r
	;Rm=Rm_pt
	;I=I_pt
	;V=V_pt
	;Rm=Rm_p
	;I=I_p
	;V=V_p
         Rm=Rm_pi
	 I=I_pi
	 V=V_pi

 ;titulo='IV_tek_r-0606'
 ;titulo='IV_tek_pt-0606'
 ;titulo='IV_tek_p-0606'
 titulo='IV_tek_pi-0606'

 set_plot,'X'
 ;window,1,xs=400,ys=250
 window,1
 plot,V,I,title=titulo,ytitle='!3I(amperes)',xtitle='V(volts)',$
 yrange=[0,.012],xrange=[-1,10],xstyle=1,background=16777215,color=0,/nodata

 Color= [255,8005000,16000000,655355,16500000,18500000];2005000
 ;titulo='IV_r_superp-1-2-4-5'
 ;titulo='IV_pt_superp-1-2-4-5'
 ;titulo='IV_p_superp-1-2-4-5'
 titulo='IV_pi_superp-1-2-4-5'

 FOR N=0, n_elements(lista)-1 do begin
     ; num=string(N)
 restore,lista(N)
	;I=I_r
	;V=V_r
	;I=I_pt
	;V=V_pt
	;I=I_p
	;V=V_p
	I=I_pi
	V=V_pi

 oplot,V,I,color=Color(N);,psym=3,symsize=0.5
 ;oplot,V,I,color=Color(N)
 XYOUTS,100,200- N * 20,'+',color=Color(N),/device
 XYOUTS,120,200-N * 20,strsplit(lista(N),'_0606.dat',/extract,/regex),$
 color=0,/device
 ENDFOR
;stop
 ;WRITE_JPEG,titulo, TVRD(/true), QUALITY=100,/true

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
