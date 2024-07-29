pro gamma ;, tek=tek,Rp=Rp
 

restore,'tek_r05_1205.dat'
archivo='tek_r05_1205'
;I=tek.ch2/Rp
;V=tek.ch1-tek.ch2

I=I_r
V=V_r

index=where(I gt 0)

Y=alog(I(index))
X=alog(V(index))

gamma= deriv(X,Y)

window,0
plot,sqrt(V(index)),gamma,title='Gamma-sqrt(V)',background=16777215,color=0,/nodata,yrange=[-4,4]
oplot,sqrt(V(index)), gamma ,color=0
oplot,sqrt(V(index)), gamma ,psym=4,color=250
XYOUTS,0.5,0.85,archivo,color=0,alignment=0.1,/normal
;write_jpeg,'Gamma-sqrt(V)_'+ archivo,tvrd(/true),quality=100,/true 
 oplot,smooth(sqrt(V(index)),5),smooth(gamma,5),color=234567888

window,5
gammas=deriv(smooth(X,5),smooth(Y,5))
plot,sqrt(V),gammas,title='Gamma-sqrt(V)',background=16777215,color=0,/nodata,yrange=[-4,4]
oplot,sqrt(V), gamma ,color=0
oplot,sqrt(V(index)), gamma ,psym=4,color=250

 ;window,2
 ;plot,sqrt(V(index)), gamma ,title='Gamma-sqrt(V)_loglog',/xlog,/ylog,background=16777215,color=0,/nodata
 ;oplot,sqrt(V(index)), gamma ,psym=4,color=0
 ;XYOUTS,0.5,0.85,archivo,color=0,alignment=0.5,/normal
 ;write_jpeg,'Gamma-sqrt(V)_loglog_'+ archivo,tvrd(/true),quality=100,/true 
 

stop

  A=fltarr(n_elements(V)-1)
 for N=0,n_elements(V)-2 do A(N)=(where(V(N)-V(N+1)) eq 0.)
 Bi=where(A eq 1) 
 ;window,3 ,title='control'
 ;plot,alog(V(Bi)),alog(I(Bi)),color=234567888,psym=4,yrange=[4,5]

 window,4
 gammaBI=deriv(alog(V(Bi)),alog(I(Bi)))
 plot,sqrt(V(Bi)), gammaBI ,title='Gamma-sqrt(V)',yrange=[-4,4],$
 background=16777215,color=0,/nodata
 oplot,sqrt(V(Bi)),gammaBI,color=250,psym=4
 XYOUTS,0.5,0.85,archivo,color=0,alignment=0.5,/normal
 XYOUTS,0.5,0.80,'saque los v repetidos que hacen tener pend infinita',color=0,alignment=0.5,/normal
 ;write_jpeg,'Gamma-sqrt(V)_BI_'+ archivo,tvrd(/true),quality=100,/true                                        

END

