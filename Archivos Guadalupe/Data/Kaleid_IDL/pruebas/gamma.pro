pro gamma ;, tek=tek,Rp=Rp
 
restore,'tek_r05_1205.dat'

;I=tek.ch2/Rp
;V=tek.ch1-tek.ch2

I=I_r
V=V_r

index=where(I gt 0)

Y=alog(abs(I(index)))
X=alog(abs(V(index)))

gamma= deriv(X,Y)

window,0,title='Gamma'
plot,sqrt(V),gamma,psym=1

window,1,title='Gamma-1/V'
plot,1/V, gamma ,psym=4
stop
; A=fltarr(n_elements(V)-1)
;for i =0,n_elements(V)-1 do A=where(V(i)-V(i+1)) eq 0.
;Bi=where(A eq 1)   
;plot,alog(V(Bi)),alog(I(Bi))
;plot,alog(V(Bi)),alog(I(Bi)),color=655355
;window,2
;plot,sqrt(V(Bi)),deriv(alog(V(bi)),alog(I(Bi))),color=655355

                                                           

END

