PRO plot_Rm14todas


;grafica Rm_I 14 y le superpongo todas las Rm05-06-07-08-09-10-11-12-13


 restore,'tek0014_1105.dat'
 ;restore,filename='tek_p14_1105.dat'
 ;restore,filename='tek_r14_1105.dat'
 
 ;bordes=intarr(2,9)
 ;a=[200,100,105,110,110,96,105,100,100]
 ;b=[890,800,805,805,810,788,800,790,790]
 ;bordes[0,*]=a
 ;bordes[1,*]=b


 ; window,1,xs=400,ys=250
 ;plot,I_r,Rm_r,title=titulo,xtitle='I',ytitle='Rm',yrange=[0,50000],$
 ; xrange=[-0.0001,0.0007],background=16777215,color=0,psym=4
 ;oplot,I_p,Rm_p,color=0,psym=4

 Color= [255,16000000,655355,]
 titulo='Rm_I14 superp-8-9-10-11-12-13-14-15'

‭ window,2,xs=400,ys=250
 titulo='Rm_I14 superp-8-9-10-11-12-13-14-15'
 plot,I,Rm,title=titulo,xtitle='I',ytitle='Rm',yrange=[0,50000],$
 xrange=[-0.0001,0.0007],background=16777215,color=0,psym=4
 
 ;,/nodata
 ;oplot,I,Rm,color=0,psym=4
 
 
 FOR N=3, 9 do begin
      num=string(N)
 restore,'tek000'+ num +'_1105.dat'
 oplot,I,Rm,color= N + 1500
 ENDFOR

 FOR M=10, 13 do begin
    ‎num=string(M)
 restore,'tek000'+ num +'_1105.dat'
 oplot,I,Rm,color= M + 1500
 ENDFOR

WRITE_JPEG,titulo, TVRD(/true), QUALITY=100,/true

END
