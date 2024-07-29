pro superposicion  

  plot,tek4.ch2(210:305),xtitle ='unidades arbitrarias',ytitle='V_pulsos',Title='!3tek004 12-05',yrange=[0,6],background=16777215,color=0,/nodata
  oplot,tek4.ch2(210:305),color=0
  oplot,tek4.ch2(358:455),color=250                 
  oplot,tek4.ch2(507:605),color=16000000            
  oplot,tek4.ch2(660:750),color=65535                

 xyouts,300,340,'--- pulso1',color=0,/device
 xyouts,300,330,'--- pulso2',color=250,/device
 xyouts,300,320,'--- pulso3',color=16000000,/device
 xyouts,300,310,'--- pulso4',color=65535,/device  

WRITE_JPEG,'tek004_pulsos_superp.jpg', TVRD(/true), QUALITY=100,/true

END
