pro rampa , tek=tek , Xi=Xi , Xf=Xf , Rp=Rp , num=num


print,'tek'+num,Rp

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


tek_r=fltarr(3,Xf-Xi+1)
tek_r(0,*)=tek.time(Xi:Xf)
tek_r(1,*)=tek.Ch1(Xi:Xf)
tek_r(2,*)=tek.Ch2(Xi:Xf)

t_r=tek.time(Xi:Xf) ; _r se refiere a la rampa
Ch1_r=tek.Ch1(Xi:Xf)
Ch2_r=tek.Ch2(Xi:Xf)
Rm_r=Rm
I_r=I
V_r=V

save,Rp,tek_r,t_r,Ch1_r,Ch2_2,Rm_r,I_r,V_r, filename='tek_r'+num+'_1205.dat'

END






