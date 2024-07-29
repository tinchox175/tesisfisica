PRO plot_Rmtodas

;--------------grafica Rm_I 14 y le superpongo todas las 
;--------------Rm05-06-08-09-11-12


 spawn,'ls tek00*_1205.dat',lista

  ;lista=[tek0005_1205.dat tek0006_1205.dat tek0008_1205.dat 
  ;tek0009_1205.dat tek0011_1205.dat tek0012_1205.dat]


 ;restore,'tek0014_1205.dat'
 ;restore,filename='tek_p14_1105.dat'
 ;restore,filename='tek_r14_1105.dat'
 ;bordes=intarr(2,9)
 ;a=[200,100,105,110,110,96,105,100,100]
 ;b=[890,800,805,805,810,788,800,790,790]
 ;bordes[0,*]=a
 ;bordes[1,*]=b

 restore,lista(0)
 titulo='Rm-I_tek-1205'
 set_plot,'X'
 window,1,xs=400,ys=250
 plot,I,Rm,title=titulo,xtitle='!3I(amperes)',ytitle='Rm(!4X!3)',$
 yrange=[0,10000],xrange=[0,0.04],background=16777215,color=0,/nodata

 Color= [255,2005000,16000000,655355,16500000,18500000]
 titulo='Rm-I_superp-5-6-8-9-11-12'

 FOR N=0, n_elements(lista)-1 do begin
     ; num=string(N)
 restore,lista(N)
 oplot,I,Rm,color=Color(N),psym=1,symsize=.5
 XYOUTS,300,200- N * 20,'+',color=Color(N),/device
 XYOUTS,320,200-N * 20,strsplit(lista(N),'_1205.dat',/extract,/regex),$
 color=0,/device
 ENDFOR

 ;FOR M=10, 13 do begin
; nume=string(M)
 ;restore,STRCOMPRESS('tek00'+ nume +'_1105.dat',/REMOVE_ALL )
 ;IF (M eq 10) THEN ps=1 ELSE ps=3 
 ;oplot,I,Rm,color= M * 1600000,psym=ps
 ;ENDFOR

WRITE_JPEG,titulo, TVRD(/true), QUALITY=100,/true
 

END
