PRO plot_RmI_rpptpi
;xxxxxxxxxxxxxxxxxxxxxxVERVERVEVR
;--------------grafica
;---------Rm-I de tek 01-02-04-05 del 0606

  ;;;;;; lee todas las rampas y las grafica o todas las piramides truncadas 
  ;;;;;; lee todas los plateau y las grafica o todos los picos

  spawn,'ls tek_r*_0606.dat',listar   ;;; la rampa
  spawn,'ls tek_pt*_0606.dat',listapt  ;;; la piramide truncada
  spawn,'ls tek_p0*_0606.dat',listap  ;;; el plateau
  spawn,'ls tek_pi*_0606.dat',listapi  ;;; el pico
  ;lista=[]

 lr=n_elements(listar)
 lpt=n_elements(listapt)
 lp=n_elements(listap)
 lpi=n_elements(listapi)

 restore,listar(0)
	Rm=Rm_r
	I=I_r
	V=V_r

 titulo='RmI_tek_rpptpi_0606'

 set_plot,'X'
 ;window,1,xs=400,ys=250
 window,1
 plot,I,Rm,title=titulo,xtitle='!3I(amperes)',ytitle='Rm(!4X!3)',$
 yrange=[0,6000],xrange=[0,0.012],background=16777215,color=0,/nodata
 
 Color= [255,8005000,16000000,655355,16500000,18500000];2005000
 titulo='RmI_sup-1-2-4-5_0606'

 FOR N=0, n_elements(listar)-1 do begin
     restore,listar(N)
	I=I_r
	V=V_r
	Rm=Rm_r
 oplot,I,Rm,color=Color(N)+2500;,psym=3,symsize=0.5
 ;oplot,I,Rm,color=Color(N)
 XYOUTS,100,300- N * 20,'-',color=Color(N)+2500,/device
 XYOUTS,120,300-N * 20,strsplit(listar(N),'_0606.dat',/extract,/regex),$
 color=0,/device
 ENDFOR

 FOR M=0, n_elements(listap)-1 do begin
     restore,listap(M)
	I=I_p
	Rm=Rm_p
 oplot,I,Rm,color=Color(M),psym=3,symsize=0.5
 ;oplot,V,I,color=Color(M)
 XYOUTS,200,300- M * 20,'...',color=Color(M),/device
 XYOUTS,220,300-M * 20,strsplit(listap(M),'_0606.dat',/extract,/regex),$
 color=0,/device
 ENDFOR

 FOR NP=0, n_elements(listapt)-1 do begin
     restore,listapt(NP)
	I=I_pt
	Rm=Rm_pt
 oplot,I,Rm,color=Color(NP),psym=1,symsize=0.5
 ;oplot,I,Rm,color=Color(NP)
 XYOUTS,300,300- NP * 20,'+',color=Color(NP),/device
 XYOUTS,320,300-NP * 20,strsplit(listapt(NP),'_0606.dat',/extract,/regex),$
 color=0,/device
 ENDFOR

FOR MI=0, n_elements(listapi)-1 do begin
     restore,listapi(MI)
	I=I_pi
	Rm=Rm_pi
 oplot,I,Rm,color=Color(MI),psym=5,symsize=1
 ;oplot,I,Rm,color=Color(MI)
 ;XYOUTS,400,140- MI * 20,'5',color=Color(MI),/device
 PLOTS,400,303-MI*20,psym=5,color=Color(MI),/device
 XYOUTS,420,300-MI * 20,strsplit(listapi(MI),'_0606.dat',/extract,/regex),$
 color=0,/device
 ENDFOR

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
