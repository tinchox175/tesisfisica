PRO functexp, X, A, F, pder 
  bx = EXP(A[1] * X) 
  F = A[0] * bx + A[2] 
 
;If the procedure is called with four parameters, calculate the 
;partial derivatives. 
  IF N_PARAMS() GE 4 THEN $ 
    pder = [[bx], [A[0] * X * bx], [replicate(1.0, N_ELEMENTS(X))]] 

;XXXXXXXXXXXXXXXX   ASI SE USA

;Define a vector of weights. 
;weights = 1.0/Y 
 
;Provide an initial guess of the function's parameters. 
;A = [10.0,-0.1,2.0] 
 
;Compute the parameters. 
;yfit = CURVEFIT(X, Y, weights, A, SIGMA, FUNCTION_NAME='functexp') 
 
END 
