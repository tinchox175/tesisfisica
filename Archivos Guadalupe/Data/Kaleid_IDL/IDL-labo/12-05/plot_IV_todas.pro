PRO plot_IV_todas

;--------------grafica I-V 14 y le superpongo todas las 
;--------------Rm05-06-08-09-11-12

 ;spawn,'ls tek00*_1205.dat',lista

  lista=['tek0005_1205.dat','tek0006_1205.dat','tek0008_1205.dat',$ 
  'tek0009_1205.dat','tek0011_1205.dat','tek0012_1205.dat']

 restore,lista(0)
 titulo='IV_tek-1205'
 set_plot,'X'
 window,1,xs=400,ys=250
 ;window,1
 plot,V,I,title=titulo,ytitle='!3I(amperes)',xtitle='V(volts)',$
 ;background=16777215,yrange=[0,0.025],xrange=[0,30],color=0,/nodata ;;;esto es para primer write
 background=16777215,yrange=[0,0.04],xrange=[0,30],color=0,/nodata

 Color= [255,2005000,16000000,655355,16500000,18500000];2005000
 titulo='IV_superp-5-6-8-9-11-12'

 FOR N=0, n_elements(lista)-1 do begin
     ; num=string(N)
 restore,lista(N)
 oplot,V,I,color=Color(N),psym=1,symsize=.5
 XYOUTS,100,200- N * 20,'+',color=Color(N),/device
 XYOUTS,120,200-N * 20,strsplit(lista(N),'_1205.dat',/extract,/regex),$
 color=0,/device
 ENDFOR
;stop
;WRITE_JPEG,titulo, TVRD(/true), QUALITY=100,/true

 num=[2,3,4,10,13,14,15,16,17]
 spawn,'ls tek_p*_1205.dat',listap
 data=listap[6:*]

stop
 ;window,2,xs=400,ys=250
 ;plot,I,Rm,title=titulo,xtitle='!3I(amperes)',ytitle='Rm(!4X!3)',$
 ;yrange=[0,10000],xrange=[0,0.02],background=16777215,color=0,/nodata

 FOR M=0, n_elements(data)-1 do begin
   ;nume=string(M)
 restore,data(M)
     I=I_p
     V=V_p
 oplot,V,I,color=0,psym=2,symsize=0.2
 XYOUTS,100,215,'**',color=0,/device
 XYOUTS,120,215,'tek_p2-17',color=0,/device
 ENDFOR
 fila='siIV_superp-5-6-8-9-11-12+p 2-3-4-10-13-14-15-16-17'
 WRITE_JPEG,fila, TVRD(/true), QUALITY=100,/true
 

END
