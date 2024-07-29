pro prueba_IVRmV, tek=tek, Xi=Xi, Xf=Xf, Rp=Rp


;Rp=2000
set_plot,'X'
window,1,title='Ch1-Ch2',xs=500,ys=450

plot,tek.time(Xi:Xf),tek.Ch1(Xi:Xf),xtitle='time(s)',ytitle='Ch1,Ch2(volts)',background=16777215,color=0,/nodata
oplot,tek.time(Xi:Xf),tek.Ch1(Xi:Xf),color=65535
oplot,tek.time(Xi:Xf),tek.Ch2(Xi:Xf),color=16000000

WRITE_JPEG, 'tek2_Ch1Ch2.jpg', TVRD(/true), QUALITY=100,/true

Rm=(tek.Ch1(Xi:Xf)-tek.Ch2(Xi:Xf))*(Rp/tek.Ch2(Xi:Xf))
V=tek.Ch1(Xi:Xf)-tek.Ch2(Xi:Xf)
I=tek.Ch2(Xi:Xf)/Rp

window,4,xsize=400,ysize=250,title='Resistencia'
plot,tek.time(Xi:Xf),Rm,xtitle='time(s)',ytitle='Rm(ohms)',background=16777215,color=0,/nodata
oplot,tek.time(Xi:Xf),Rm,color=255

window,5,xsize=400,ysize=250,title='Corriente'
plot,tek.time(Xi:Xf),I,xtitle='time(s)',background=16777215,color=0,/nodata
oplot,tek.time(Xi:Xf),I,color=50000

window,2,title='V-I',xs=400,ys=250
plot,V,I, xtitle='V(volts)', ytitle='I(amperes)',background=16777215,color=0,/nodata
oplot,V,I,color=8005000

window,3,title='Rm-I',xs=450,ys=250
plot,I,Rm, xtitle='I(amperes)', ytitle='Rm(ohms)',background=16777215,color=0,/nodata
oplot,I,Rm,color=255

;WRITE_JPEG,'guadapruebas.jpg', TVRD(/true), QUALITY=100,/true
;set_plot,

t_p=tek.time(Xi:Xf) ; _p se refiere al pulso
Ch1_p=tek.Ch1(Xi:Xf)
Ch2_p=tek.Ch2(Xi:Xf)
Rm_p=Rm
I_p=I
V_p=V
;save,t_p,Ch1_p,Ch2_p,Rm_p,I_p,V_p,filename='tek005_1205_p.dat'

end


