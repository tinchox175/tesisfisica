 PRO plot_pirtrun, tek=tek , Xi=Xi , Xf=Xf , Rp=Rp , num=num


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
 yrange=[0,5000],background=16777215,color=0,/nodata
 oplot,I,Rm,color=255


 tek_pt=fltarr(6,Xf-Xi+1)
 tek_pt(0,*)=tek.time(Xi:Xf)
 tek_pt(1,*)=tek.Ch1(Xi:Xf)
 tek_pt(2,*)=tek.Ch2(Xi:Xf)
 tek_pt(3,*)=Rm
 tek_pt(4,*)=I
 tek_pt(5,*)=V

 t_pt=tek.time(Xi:Xf) ; _pt se refiere a la piramide truncada
 Ch1_pt=tek.Ch1(Xi:Xf)
 Ch2_pt=tek.Ch2(Xi:Xf)
 Rm_pt=Rm
 I_pt=I
 V_pt=V


 save,Rp,tek_pt,t_pt,Ch1_pt,Ch2_pt,Rm_pt,I_pt,V_pt, filename='tek_pt'+num+'_0606.dat'


 s=size(tek_pt,/dimension)
 
  xs=s[0]
  stek_pt=strtrim(tek_pt,2)
  stek_pt[0:xs-2,*]=stek_pt[0:xs-2,*]+','

 header=strarr(6,1)
 header=['time,' ,'Ch1,' ,'Ch2,' ,'Rm,' ,'I=Ch2/'+strtrim(Rp,2)+',' , 'V=Ch1-Ch2']


 file='tek_pt'+num+'_0606.csv'
 openw,1,file 
 printf,1,header  
 printf,1,stek_pt                
 free_lun,1     

END


