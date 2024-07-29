PRO pulsosRmI

 spawn,'ls tek_p*04_1205.dat',lis
 ;spawn,'ls tek_p*10_1205.dat',lis
 ;spawn,'ls tek_p*13_1205.dat',lis
 ;spawn,'ls tek_p*14_1205.dat',lis
 ;spawn,'ls tek_p*15_1205.dat',lis
 ;spawn,'ls tek_p*16_1205.dat',lis
 ;spawn,'ls tek_p*17_1205.dat',lis
 
 restore,lis(0)
 titulo= strmid(strmid(lis(0),0,13),6,7)

 window,1,xsize=400,ysize=300
 plot,I_p,Rm_p,background=16777215,color=0,$
 title='tek_p'+titulo,xtitle='!3Corriente',ytitle='Rm(!4X!3)',/nodata,$
 yrange=[min(Rm_p)-1000,max(Rm_p)+1000],xrange=[min(I_p)-0.00001,max(I_p)+0.00005]
 XYOUTS,250,200,strcompress(string(n_elements(lis)))+'_pulsos',color=0,/device

 FOR N=0, n_elements(lis)-1 DO BEGIN
 restore,lis(N)
   Np=strcompress(string(N+1))
 oplot,I_p,Rm_p,color=255 + N*15000 ,psym=1
 ;oplot,smooth(I_p,4),smooth(Rm_p,4),color=255 + N*15000,psym=1
 XYOUTS,310,220 - N*10 ,'+  p'+ Np,color=255 + N *15000,/device
 ENDFOR
 WRITE_JPEG,'tek_p'+titulo+'.jpeg', TVRD(/true), QUALITY=100,/true
;stop
 
END
