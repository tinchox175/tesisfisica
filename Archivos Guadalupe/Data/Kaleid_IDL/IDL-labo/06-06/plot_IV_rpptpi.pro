PRO plot_IV_rpptpi
;xxxxxxxxxxxxxxxxxxxxxxVERVERVEVR
;--------------grafica I-V 
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

 titulo='IV_tek_rpptpi_0606'

 set_plot,'X'
 ;window,1,xs=400,ys=250
 window,1
 plot,V,I,title=titulo,ytitle='!3I(amperes)',xtitle='V(volts)',$
 yrange=[0,.012],xrange=[-1,10],xstyle=1,background=16777215,color=0,/nodata

 Color= [255,8005000,16000000,655355,16500000,18500000];2005000
 titulo='IV_sup-1-2-4-5_0606'

 FOR N=0, n_elements(listar)-1 do begin
     restore,listar(N)
	I=I_r
	V=V_r
 oplot,V,I,color=Color(N);,psym=3,symsize=0.5
 ;oplot,V,I,color=Color(N)
 XYOUTS,100,200- N * 20,'-',color=Color(N),/device
 XYOUTS,120,200-N * 20,strsplit(listar(N),'_0606.dat',/extract,/regex),$
 color=0,/device
 ENDFOR

 FOR M=0, n_elements(listap)-1 do begin
     restore,listap(M)
	I=I_p
	V=V_p
 oplot,V,I,color=Color(M),psym=3,symsize=0.5
 ;oplot,V,I,color=Color(M)
 XYOUTS,100,300- M * 20,'...',color=Color(M),/device
 XYOUTS,120,300-M * 20,strsplit(listap(M),'_0606.dat',/extract,/regex),$
 color=0,/device
 ENDFOR

 FOR NP=0, n_elements(listapt)-1 do begin
     restore,listapt(NP)
	I=I_pt
	V=V_pt
 oplot,V,I,color=Color(NP),psym=1,symsize=0.5
 ;oplot,V,I,color=Color(NP)
 XYOUTS,300,140- NP * 20,'+',color=Color(NP),/device
 XYOUTS,320,140-NP * 20,strsplit(listapt(NP),'_0606.dat',/extract,/regex),$
 color=0,/device
 ENDFOR

FOR MI=0, n_elements(listapi)-1 do begin
     restore,listapi(MI)
	I=I_pi
	V=V_pi
 oplot,V,I,color=Color(MI),psym=5,symsize=1
 ;oplot,V,I,color=Color(MI)
 ;XYOUTS,400,140- MI * 20,'5',color=Color(MI),/device
 PLOTS,400,143-MI*20,psym=5,color=Color(MI),/device
 XYOUTS,420,140-MI * 20,strsplit(listapi(MI),'_0606.dat',/extract,/regex),$
 color=0,/device
 ENDFOR

;stop
 ;WRITE_JPEG,titulo, TVRD(/true), QUALITY=100,/true


END
