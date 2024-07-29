PRO plot_IVRmI_ALL

;--------------grafica I-V 
;---------Rm-I de tekr 01-02-04-05 del 0606

  ;;;;;; lee todas las rampas del 0606
  ;;;;;; lee todas los plateau y las grafica o todos los picos

  spawn,'ls 06-06/tek_r*_0606.dat',lista06   ;;; 
  spawn,'ls 12-05/tek_r*_1205.dat',lista12  ;;; 
  spawn,'ls 11-05/tek_r*_1105.dat',lista11  ;;; 
  lista=[lista11,lista12,lista06]


   	;lista=[‪11-05/tek_r03_1105.dat 11-05/tek_r04_1105.dat 11-05/tek_r05_1105.dat
	;11-05/tek_r06_1105.dat 11-05/tek_r07_1105.dat 11-05/tek_r08_1105.dat
	;11-05/tek_r09_1105.dat 11-05/tek_r10_1105.dat 11-05/tek_r11_1105.dat
	;11-05/tek_r12_1105.dat 11-05/tek_r13_1105.dat 11-05/tek_r14_1105.dat
	;12-05/tek_r05_1205.dat 12-05/tek_r06_1205.dat 12-05/tek_r08_1205.dat
	;12-05/tek_r09_1205.dat 12-05/tek_r11_1205.dat 12-05/tek_r12_1205.dat
	;06-06/tek_r01_0606.dat 06-06/tek_r02_0606.dat 06-06/tek_r04_0606.dat
	;06-06/tek_r05_0606.dat]

  sz06=n_elements(lista06)
  sz11=n_elements(lista11)
  sz12=n_elements(lista12)

 restore,lista(0)
	Rm=Rm_r
	I=I_r
	V=V_r
	
 titulo='IV_tek_r-1105-1205-0606'

 set_plot,'X'
 ;window,1,xs=400,ys=250
 ;window,1
 window,1,xs=800,ys=500
 plot,V,I,title=titulo,ytitle='!3I(amperes)',xtitle='V(volts)',$
 yrange=[0,.015],xrange=[-1,30],xstyle=1,background=16777215,$
 color=0,/nodata;,/xlog,/ylog

 Color= [255,8005000,16000000,655355,16500000,18500000];2005000
 colorete=indgen(n_elements(lista),/long)
 colorete[0:sz11-1]=255
 colorete[sz11:sz11+sz12-1]=16000000
 colorete[sz11+sz12:*]=18500000
 stop
 FOR N=0, n_elements(lista)-1 do begin
     ; num=string(N)
 restore,lista(N)
        Rm=Rm_r
	I=I_r
	V=V_r
 oplot,V,I,color=colorete(N),psym=1,symsize=0.5
 ENDFOR
 XYOUTS,100,300,'+',color=colorete(0),/device
 XYOUTS,120,300,'tek_r*_1105',color=0,/device
 XYOUTS,100,320,'+',color=colorete(13),/device
 XYOUTS,120,320,'tek_r*_1205',color=0,/device
 XYOUTS,100,340,'+',color=colorete(21),/device
 XYOUTS,120,340,'tek_r*_0606',color=0,/device
 
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
