 PRO agregarcoma

  ;spawn,'ls tek_r*_1205.dat',lista
 spawn,'ls tek_p*_1205.dat',lista
  data=lista

 FOR N=0,n_elements(data)-1 DO BEGIN
  restore,data(N)

  ;s=size(tek_r,/dimension)
 s=size(tek_p,/dimension)
 
  xs=s[0]
 
  ;stek_r=strtrim(tek_r,2)
 stek_p=strtrim(tek_p,2)
 
  nombre= STRSPLIT(data(N),'.dat',/REGEX,/EXTRACT)
  linewidth=1600

  header=strarr(6,1)
  header=['time,' ,'Ch1,' ,'Ch2,' ,'Rm,' ,'I=Ch2/'+ strtrim(Rp,2)+',' , 'V=Ch1-Ch2']

 
  ;stek_r[0:xs-2,*]=stek_r[0:xs-2,*]+','
 stek_p[0:xs-2,*]=stek_p[0:xs-2,*]+','
 
  openW,lun,nombre +'.csv',/Get_lun,width=linewidth
  printf,lun,header
  ;printf,lun,stek_r
 printf,lun,stek_p
  free_lun,lun

 ENDFOR
 END
