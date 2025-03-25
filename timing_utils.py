#!/usr/bin/env python3
"""
Timing utility module for Stone Email Processor
Provides accurate timing measurement for both backend processing and UI display
"""
import time
import functools
import threading
import json
import os
from typing import Dict, List, Optional, Any, Callable

class TimingManager:
    """
    Manager for tracking operation-specific timing metrics
    Separates processing time from UI uptime
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TimingManager, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        self.timers: Dict[str, Dict[str, float]] = {}
        self.completed_operations: List[Dict[str, Any]] = []
        self.start_time = time.time()
        
    def reset_all(self):
        """Reset all timers and metrics"""
        self.timers = {}
        self.completed_operations = []
        self.start_time = time.time()
    
    def start_timer(self, operation_name: str) -> str:
        """Start a timer for a specific operation"""
        timer_id = f"{operation_name}_{time.time()}"
        self.timers[timer_id] = {
            'operation': operation_name,
            'start_time': time.time(),
            'end_time': None,
            'duration': None
        }
        return timer_id
    
    def stop_timer(self, timer_id: str) -> Optional[float]:
        """Stop a timer and record its duration"""
        if timer_id not in self.timers:
            return None
        
        self.timers[timer_id]['end_time'] = time.time()
        duration = self.timers[timer_id]['end_time'] - self.timers[timer_id]['start_time']
        self.timers[timer_id]['duration'] = duration
        
        # Add to completed operations
        self.completed_operations.append({
            'operation': self.timers[timer_id]['operation'],
            'start_time': self.timers[timer_id]['start_time'],
            'end_time': self.timers[timer_id]['end_time'],
            'duration': duration
        })
        
        return duration
    
    def get_operation_time(self, operation_name: str) -> float:
        """Get the total time spent on a specific operation"""
        total_time = 0.0
        for op in self.completed_operations:
            if op['operation'] == operation_name:
                total_time += op['duration']
        return total_time
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all timing metrics"""
        total_processing_time = sum(op['duration'] for op in self.completed_operations)
        uptime = time.time() - self.start_time
        
        # Group by operation type
        operation_times = {}
        for op in self.completed_operations:
            op_name = op['operation']
            if op_name not in operation_times:
                operation_times[op_name] = 0
            operation_times[op_name] += op['duration']
        
        return {
            'total_processing_time': total_processing_time,
            'uptime': uptime,
            'idle_time': uptime - total_processing_time,
            'operations': operation_times,
            'operation_history': self.completed_operations
        }
    
    def export_metrics(self, filepath: str) -> bool:
        """Export metrics to a JSON file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.get_all_metrics(), f, indent=2)
            return True
        except Exception:
            return False

# Decorator for timing functions
def timed_operation(operation_name: str = None):
    """Decorator to time a function and record metrics"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            timer_manager = TimingManager()
            op_name = operation_name or func.__name__
            timer_id = timer_manager.start_timer(op_name)
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = timer_manager.stop_timer(timer_id)
                # Optional: Add logging here if needed
        return wrapper
    return decorator

# Get singleton instance
def get_timing_manager() -> TimingManager:
    """Get the singleton TimingManager instance"""
    return TimingManager()
