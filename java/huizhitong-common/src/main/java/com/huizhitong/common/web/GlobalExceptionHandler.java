package com.huizhitong.common.web;

import com.huizhitong.common.api.ApiResult;
import com.huizhitong.common.api.ResultCode;
import com.huizhitong.common.exception.BusinessException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.ConstraintViolationException;
import org.slf4j.MDC;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<ApiResult<Void>> handleBusiness(BusinessException ex) {
        return ResponseEntity.ok(ApiResult.failure(ex.getCode(), ex.getMessage(), traceId()));
    }

    @ExceptionHandler({MethodArgumentNotValidException.class, ConstraintViolationException.class})
    public ResponseEntity<ApiResult<Void>> handleValidation(Exception ex) {
        return ResponseEntity.badRequest().body(ApiResult.failure(ResultCode.BAD_REQUEST, traceId()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResult<Void>> handleUnknown(Exception ex, HttpServletRequest request) {
        return ResponseEntity.internalServerError().body(ApiResult.failure(ResultCode.INTERNAL_ERROR, traceId()));
    }

    private String traceId() {
        String traceId = MDC.get(TraceIdFilter.TRACE_ID);
        return traceId == null ? "" : traceId;
    }
}
