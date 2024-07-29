pro func_strechfit,X,A,F,pder


F=A[0]*exp(-(X/A[2])^A[3])+A[1]

 IF N_PARAMS() GE 4 THEN BEGIN 
      ; PDER's column dimension is equal to the number of 
      ; elements in xi and its row dimension is equal to  
      ; the number of parameters in the function F: 
    pder = FLTARR(N_ELEMENTS(X), 4) 
      ; Compute the partial derivatives with respect to 
      ; a0 and place in the first row of PDER: 
     pder[*, 0] = EXP(-(X/A[2])^A[3])
      ; Compute the partial derivatives with respect to 
      ; a1 and place in the second row of PDER: 
     pder[*, 1] = 1.
     pder[*, 2] = (A[0]*A[3]*(X/A[2])^A[3] * EXP(-(X/A[2])^A[3]))/A[2]
     pder[*, 3] = -A[0]*((X/A[2])^A[3])*alog(X/A[2])*EXP(-(X/A[2])^A[3])
  ENDIF 

END
 
