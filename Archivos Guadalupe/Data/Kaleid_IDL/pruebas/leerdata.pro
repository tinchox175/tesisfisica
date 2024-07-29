pro leerdata, tek=tek, Rp=Rp
 ; leo y salvo t,ch1,ch2,Rm,I,V y Xi,Xf son los elementos para los cuales salve

data=['tek0003ALL.csv','tek0004ALL.csv','tek0005ALL.csv','tek0006ALL.csv',$
'tek0007ALL.csv','tek0008ALL.csv','tek0009ALL.csv','tek0010ALL.csv',$
'tek0011ALL.csv','tek0012ALL.csv','tek0013ALL.csv'] 

 a=[150,181,200,100,105,110,110,96,105,100,100] ;te03 al tek13
 b=[850,880,890,800,805,805,810,788,800,790,790]
 Rpatron=[10000,10000,10000,10000,10000,10000,10000,10000,10000,4000,4000]

restore,filename='guadatemplate.sav'

 FOR i=0,10 DO BEGIN
  tek=read_ascii(data(i),template=guada)

  Xi=a(i)
  Xf=b(i)
  Rp=Rpatron(i)

  Rm=(tek.Ch1(Xi:Xf)-tek.Ch2(Xi:Xf))*(Rp/tek.Ch2(Xi:Xf))
  V=tek.Ch1(Xi:Xf)-tek.Ch2(Xi:Xf)
  I=tek.Ch2(Xi:Xf)/Rp
  titulo=strmid(data(i),0,7)+'_1105'


set_plot,'X'
window,1,title='Ch1-Ch2',xs=500,ys=450

plot,tek.time(Xi:Xf),tek.Ch1(Xi:Xf),title=titulo,xtitle='time(s)',ytitle='Ch1,Ch2(volts)',background=16777215,color=0,/nodata
oplot,tek.time(Xi:Xf),tek.Ch1(Xi:Xf),color=65535
oplot,tek.time(Xi:Xf),tek.Ch2(Xi:Xf),color=16000000

WRITE_JPEG, titulo + '.jpg', TVRD(/true), QUALITY=100,/true

window,4,xsize=400,ysize=250,title='Resistencia'
plot,tek.time(Xi:Xf),Rm,xtitle='time(s)',ytitle='Rm(ohms)',background=16777215,color=0,/nodata
oplot,tek.time(Xi:Xf),Rm,color=255
WRITE_JPEG, 'Rm'+ titulo + '.jpg', TVRD(/true), QUALITY=100,/true

window,5,xsize=400,ysize=250,title='Corriente'
plot,tek.time(Xi:Xf),I,xtitle='time(s)',background=16777215,color=0,/nodata
oplot,tek.time(Xi:Xf),I,color=50000
WRITE_JPEG, 'I'+ titulo + '.jpg', TVRD(/true), QUALITY=100,/true

window,2,title='I-V',xs=400,ys=250
plot,V,I, xtitle='V(volts)', ytitle='I(amperes)',background=16777215,color=0,/nodata
oplot,V,I,color=8005000
WRITE_JPEG, 'I-V'+ titulo + '.jpg', TVRD(/true), QUALITY=100,/true

window,3,title='Rm-I',xs=450,ys=250
plot,I,Rm, xtitle='I(amperes)', ytitle='Rm(ohms)',background=16777215,color=0,/nodata
oplot,I,Rm,color=255
WRITE_JPEG, 'Rm-V'+ titulo + '.jpg', TVRD(/true), QUALITY=100,/true

t=tek.time(Xi:Xf) ; 
Ch1=tek.Ch1(Xi:Xf)
Ch2=tek.Ch2(Xi:Xf)
;Rm_p=Rm
;I_p=I
;V_p=V
save,t,Ch1,Ch2,Rm,I,V,Xi,Xf,Rp,filename=titulo +'.dat'

ENDFOR

end


