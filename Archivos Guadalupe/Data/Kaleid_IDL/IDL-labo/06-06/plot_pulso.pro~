pro plot_pulso, tek=tek , Xi=Xi , Xf=Xf , Rp=Rp , num=num
 
 ;;;;;;;;;;esta hecho para el pulso y el pico fijarse a bajo que esta guardadao

print,'tek'+num,Rp

Rm=(tek.Ch1(Xi:Xf)-tek.Ch2(Xi:Xf))*(Rp/tek.Ch2(Xi:Xf))
V=tek.Ch1(Xi:Xf)-tek.Ch2(Xi:Xf)
I=tek.Ch2(Xi:Xf)/Rp


window,4,xsize=400,ysize=250,title='Resistencia'
plot,tek.time(Xi:Xf),Rm,xtitle='time(s)',ytitle='Rm(ohms)',background=16777215,color=0,/nodata
oplot,tek.time(Xi:Xf),Rm,color=255

window,5,xsize=400,ysize=250,title='Corriente'
plot,tek.time(Xi:Xf),I,xtitle='time(s)',ytitle='I',background=16777215,color=0,/nodata
oplot,tek.time(Xi:Xf),I,color=50000

window,2,title='V-I',xs=400,ys=250
plot,V,I, xtitle='V(volts)', ytitle='I(amperes)',background=16777215,color=0,/nodata
oplot,V,I,color=8005000

window,3,title='Rm-I',xs=450,ys=250
plot,I,Rm, xtitle='I(amperes)', ytitle='Rm(ohms)',$
ystyle=16,background=16777215,color=0,/nodata
oplot,I,Rm,color=255


tek_p=fltarr(6,Xf-Xi+1)
tek_p(0,*)=tek.time(Xi:Xf)
tek_p(1,*)=tek.Ch1(Xi:Xf)
tek_p(2,*)=tek.Ch2(Xi:Xf)
tek_p(3,*)=Rm
tek_p(4,*)=I
tek_p(5,*)=V

t_p=tek.time(Xi:Xf) ; _p se refiere a la pulso ;_pi poner el pico
Ch1_p=tek.Ch1(Xi:Xf)
Ch2_p=tek.Ch2(Xi:Xf)
Rm_p=Rm
I_p=I
V_p=V
tek_p=tek_p

;save,Rp,tek_p,t_p,Ch1_p,Ch2_p,Rm_p,I_p,V_p, filename='tek_p'+num+'_1205.dat'
;save,Rp,tek_p,t_p,Ch1_p,Ch2_p,Rm_p,I_p,V_p, filename='tek_p'+num+'_1105.dat'
save,Rp,tek_p,t_p,Ch1_p,Ch2_p,Rm_p,I_p,V_p, filename='tek_p'+num+'_0606.dat'
;save,Rp,tek_pi,t_pi,Ch1_pi,Ch2_pi,Rm_pi,I_pi,V_pi, filename='tek_pi'+num+'_0606.dat'

 s=size(tek_p,/dimension)
 
  xs=s[0]
  stek_p=strtrim(tek_p,2)
  stek_p[0:xs-2,*]=stek_p[0:xs-2,*]+','

header=strarr(6,1)
header=['time,' ,'Ch1,' ,'Ch2,' ,'Rm,' ,'I=Ch2/'+strtrim(Rp,2)+',' , 'V=Ch1-Ch2']

;file='tek_p'+num+'_1205.txt'
;file='tek_p'+num+'_1105.txt'
file='tek_p'+num+'_0606.csv'
;file='tek_pi'+num+'_0606.csv'
openw,1,file 
printf,1,header  
printf,1,stek_p                
free_lun,1     

END


