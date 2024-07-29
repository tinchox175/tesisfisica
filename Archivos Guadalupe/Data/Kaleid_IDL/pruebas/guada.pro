x=-5+findgen(1001)*0.01

seed=1001L
yy=randomu(seed,101)*0.4
xx=-5+findgen(51)*0.2

tvlct,[0,255,0,0],[0,0,255,0],[0,0,0,255]

window,0,xs=600,ys=650
plot,x,x^2,charsize=1.3,charthick=1.6,thick=2.5,xtitle='!8Abcisas Guada',$
ytitle='Datos Guada',yrange=[-1,25],ystyle=1,xrange=[-5,5],/nodata,$
title='!8Desvarios de Acha',xstyle=1,backg=255,color=0
oplot,x,x^2,color=3,thick=2
oplot,xx+yy*0.3,xx^2+yy,psym=4,color=2,thick=2


a=tvrd(/true)
write_png,'guada.png',a
WRITE_JPEG, 'guada.jpg', TVRD(/true), QUALITY=100,/true

end
