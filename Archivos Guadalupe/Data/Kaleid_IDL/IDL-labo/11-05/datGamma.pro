pro datGamma


restore,'tek_r14_1105.dat'
nombre='gammadat_tek_r14_1105'

lnI=alog(I_r)
lnV=alog(V_r)
sqrt_V=sqrt(V_r)
S10_I=smooth(I_r,10,/edge_truncate)
S10_V=smooth(V_r,10,/edge_truncate)
lnS10_I=alog(S10_I)
lnS10_V=alog(S10_V)
sqrt_S10V=sqrt(S10_V)
S5_I=smooth(I_r,5,/edge_truncate)
S5_V=smooth(V_r,5,/edge_truncate)
lnS5_I=alog(S5_I)
lnS5_V=alog(S5_V)
sqrt_S5V=sqrt(S5_V)
S20_I=smooth(I_r,20,/edge_truncate)
S20_V=smooth(V_r,20,/edge_truncate)
lnS20_I=alog(S20_I)
lnS20_V=alog(S20_V)
sqrt_S20V=sqrt(S20_V)
S50_I=smooth(I_r,50,/edge_truncate)
S50_V=smooth(V_r,50,/edge_truncate)
lnS50_I=alog(S50_I)
lnS50_V=alog(S50_V)
sqrt_S50V=sqrt(S50_V)


dat=fltarr(23,n_elements(I_r))
dat[0,*]=alog(I_r)
dat[1,*]=alog(V_r)
dat[2,*]=sqrt(V_r)
dat[3,*]=smooth(I_r,5,/edge_truncate)
dat[4,*]=smooth(V_r,5,/edge_truncate)
dat[5,*]=alog(S5_I)
dat[6,*]=alog(S5_V)
dat[7,*]=sqrt(S5_V)
dat[8,*]=smooth(I_r,10,/edge_truncate)
dat[9,*]=smooth(V_r,10,/edge_truncate)
dat[10,*]=alog(S10_I)
dat[11,*]=alog(S10_V)
dat[12,*]=sqrt(S10_V)

dat[13,*]=smooth(I_r,20,/edge_truncate)
dat[14,*]=smooth(V_r,20,/edge_truncate)
dat[15,*]=alog(S20_I)
dat[16,*]=alog(S20_V)
dat[17,*]=sqrt(S20_V)
dat[18,*]=smooth(I_r,50,/edge_truncate)
dat[19,*]=smooth(V_r,50,/edge_truncate)
dat[20,*]=alog(S50_I)
dat[21,*]=alog(S50_V)
dat[22,*]=sqrt(S50_V)

;stop

header=['lnI,','lnV,','sqrt_V,','S5_I,','S5_V,','lnS5_I,','lnS5_V,',$
'sqrt_S5V,','S10_I,','S10_V,','lnS10_I,','lnS10_V,','sqrt_S10V,',$
'S20_I,','S20_V,','lnS20_I,','lnS20_V,','sqrt_S20V,',$
'S50_I,','S50_V,','lnS50_I,','lnS50_V,','sqrt_S50V,']

sdat=strtrim(dat,2)

xs=23
sdat[0:xs-2,*]=sdat[0:xs-2,*]+','
 ;stop
save,dat,filename=nombre+'.dat'
 linewidth=1600

openW,lun,nombre + '.csv',/Get_lun,width=linewidth
  printf,lun,header
  printf,lun,sdat
  free_lun,lun
END

