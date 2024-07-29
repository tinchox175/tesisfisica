PRO pulsosI16

 restore,'tek_pa16_1105.dat'
 t_pa=t_p
 Ch1_pa=Ch1_p
 Ch2_pa=Ch2_p
 I_pa=I_p
 V_pa=V_p
 Rm_pa=Rm_p

 restore,'tek_pb16_1105.dat'
 II=[I_pa,I_p]
 window,1,xsize=400,ysize=300
 plot,II,RM_pa,background=16777215,color=0,$
 title='tek16 dos pulsos',xtitle='corriente',$
 ytitle='Rm',/nodata,xrange=[.0004,.0005],yrange=[10000,14000]
 Xyouts,300,260,'pulso 1',color=255,/device
 Xyouts,300,240,'pulso 2',color=16000000 ,/device
 oplot,I_p,Rm_p,color=16000000,psym=4                                 
 oplot,I_pa,Rm_pa,color=255,psym=1  
 WRITE_JPEG,'tek16_dospulsos.jpeg', TVRD(/true), QUALITY=100,/true
 oplot,I_p,Rm_p,color=16000000                                
 oplot,I_pa,Rm_pa,color=255        
 WRITE_JPEG,'tek16_dpulsos.jpeg', TVRD(/true), QUALITY=100,/true
   
END
