pro  csv13

;restore ,'tek0013rp1_1205.dat'
;nombre='tek0013rp1_1205'

;restore ,'tek0013rp2_1205.dat'
;nombre='tek0013rp2_1205'

;restore ,'tek0015rp1_1205.dat'
;nombre='tek0015rp1_1205'

restore ,'tek0015rp2_1205.dat'
nombre='tek0015rp2_1205'

tek=fltarr(6,n_elements(t))
tek[0,*]=t
tek[1,*]=Ch1
tek[2,*]=Ch2
tek[3,*]=Rm
tek[4,*]=I
tek[5,*]=V

s=size(tek,/dimension)
 
  xs=s[0]
 
 
 stek=strtrim(tek,2)
 
  ;nombre= STRSPLIT(data(N),'.dat',/REGEX,/EXTRACT)
  linewidth=1600

  header=strarr(6,1)
  header=['time,' ,'Ch1,' ,'Ch2,' ,'Rm,' ,'I=Ch2/'+ strtrim(Rp,2)+',' , 'V=Ch1-Ch2']

 
 stek[0:xs-2,*]=stek[0:xs-2,*]+','
 
  openW,lun,nombre +'.csv',/Get_lun,width=linewidth
  printf,lun,header
  printf,lun,stek
  free_lun,lun
END


