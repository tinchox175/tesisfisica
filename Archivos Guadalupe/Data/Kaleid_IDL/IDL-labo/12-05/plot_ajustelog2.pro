PRO plot_ajustelog2

   restore,'tek0011_1205.dat'
 titulo='Ajustelog2_tek11_1205'
   A=[0.0000001,0.0001,0.2]

  logsult=comfit(v[2:50],i[2:50],A,/logsquare,yfit=ylog)

   y=logsult[0]+logsult[1] * alog(v[2:50]) + logsult[2] * (alog(v[2:50]))^2
       
   print,logsult
 ; 0.000900688     0.669921 -0.000879287
  funcion='Y='   

 window,1
 plot,v[2:50],I[2:50],background=16777215,color=0,$
 title=titulo,ytitle='I(amperes)',xtitle='V(volts)',/nodata                   
 oplot,v[2:50],I[2:50],color=0    
 oplot,v[2:50],y,color=1600000 
 xyouts,0.5,0.85,funcion ,color=0,alignment=0.5,/normal
       
 ;write_jpeg,'ajustelog2_tek11_1205.jpeg',tvrd(/true),quality=100,/true 

END
