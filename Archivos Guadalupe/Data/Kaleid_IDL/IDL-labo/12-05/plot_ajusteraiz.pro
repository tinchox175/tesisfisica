PRO plot_ajusteraiz

   restore,'tek0011_1205.dat'
 titulo='Ajusteraiz_tek11_1205'
   A=[1,.5,2]

   rsult=comfit(v[2:50],i[2:50],A,/geometric)

   y=rsult[0]*v[2:50]^rsult[1]+rsult[2]
       
   print,rsult
 ; 0.000900688     0.669921 -0.000879287
  funcion='Y= 0.0009 * X^0.669921 -0.00879287'   

 window,1
 plot,v[2:50],I[2:50],background=16777215,color=0,$
 title=titulo,ytitle='I(amperes)',xtitle='V(volts)',/nodata                   
 oplot,v[2:50],I[2:50],color=0    
 oplot,v[2:50],y,color=1600000 
 xyouts,0.5,0.85,funcion ,color=0,alignment=0.5,/normal
       
 write_jpeg,'ajusteraiz_tek11_1205.jpeg',tvrd(/true),quality=100,/true 

END
