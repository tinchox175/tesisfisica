PRO plot_energia

 restore,'Energia_pulsos_1205.dat'

 titulo='Energia-Dt_1205'
 window,1,xs=500,ys=400

 plot,dt,et,title= 'Energia-!4D!3t'+'_1205',xtitle='!4D!3t',ytitle='Energia',$
 background=16777215,color=0, psym=1
;stop
 daux=[dt(1),dt(3),dt(4),dt(19),dt(33),dt(34)]
 eaux=[et(1),et(3),et(4),et(19),et(33),et(34)]
 oplot,daux,eaux,color=255, psym=4

;stop
 ;WRITE_JPEG, titulo + '.jpeg', TVRD(/true), QUALITY=100,/true
 
 window,2,xs=500,ys=400
 plot,dt,et,title= 'Energia-!4D!3t'+'_1205',xtitle='!4D!3t',ytitle='Energia',$
 background=16777215,color=0, psym=1,/xlog,/ylog
 oplot,daux,eaux,color=255, psym=4
 ;WRITE_JPEG, titulo + 'log.jpeg', TVRD(/true), QUALITY=100,/true

END
