PRO plot_IVRmV

data=['tek_p03_1105.dat','tek_p07_1105.dat','tek_p11_1105.dat',$
'tek_pa16_1105.dat','tek_p04_1105.dat','tek_p08_1105.dat','tek_p12_1105.dat','tek_pa17_1105.dat',$
'tek_p05_1105.dat','tek_p09_1105.dat','tek_p13_1105.dat','tek_pb16_1105.dat'$
,'tek_p06_1105.dat','tek_p10_1105.dat','tek_p14_1105.dat','tek_pb17_1105.dat']

Lsize=size(data,/dimension)

FOR N=0,n_elements(data)-1 DO BEGIN
 
 restore,filename=data(N)

;////////////////////////////////////////////////////////
;ENDFOR
;///////////////////////////////////////////////////////

set_plot,'X'
window,1,title='Ch1-Ch2',xs=400,ys=250

plot,t_p,Ch1_p,xtitle='time(s)',ytitle='Ch1,Ch2(volts)',background=16777215,color=0,/nodata
oplot,t_p,Ch1_p,color=65535
oplot,t_p,Ch2_p,color=16000000

WRITE_JPEG, StrSplit(data[N],'.dat',/Regex, /Extract) + '.jpeg', TVRD(/true), QUALITY=100,/true


window,4,xsize=400,ysize=250,title='Resistencia'
plot,t_p,Rm_p,xtitle='time(s)',ytitle='Rm(ohms)',background=16777215,color=0,/nodata
oplot,t_p,Rm_p,color=255

window,5,xsize=400,ysize=250,title='Corriente'
plot,t_p,I_p,xtitle='time(s)',background=16777215,color=0,/nodata
oplot,t_p,I_p,color=50000

window,2,title='I-V',xs=400,ys=250
plot,V_p,I_p, xtitle='V(volts)', ytitle='I(amperes)',background=16777215,color=0,/nodata
oplot,V_p,I_p,color=8005000

window,3,title='Rm-I',xs=450,ys=250
plot,I_p,Rm_p, xtitle='I(amperes)', ytitle='Rm(ohms)',background=16777215,color=0,/nodata
oplot,I_p,Rm_p,color=255

;WRITE_JPEG,'nombre', TVRD(/true), QUALITY=100,/true
;set_plot,


endfor

END
 
