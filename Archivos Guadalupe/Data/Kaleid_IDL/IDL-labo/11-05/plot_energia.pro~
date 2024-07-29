PRO plot_energia

 restore,'Energia_pulsos_1105.dat'

 titulo='Energia-Dt_1105'
 window,1,xs=500,ys=400

 plot,dt,et,title= 'Energia-!4D!3t_1105',xtitle='!4D!3t',ytitle='Energia',$
 background=16777215,color=0, psym=1

 daux=[0,dt(6)]
 eaux=[0,et(6)]
 oplot,daux,eaux,color=255, psym=4

 daux2=[0,dt(7)]
 eaux2=[0,et(7)]
 oplot,daux2,eaux2,color=16000000, psym=1

;stop
 WRITE_JPEG, titulo + '.jpeg', TVRD(/true), QUALITY=100,/true

END
