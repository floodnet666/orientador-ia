'use client'
import React, { useState } from 'react'
import { useHelp } from '@/store/HelpContext'

interface HelpTooltipProps {
    children: React.ReactNode
    content: string
    position?: 'top' | 'bottom' | 'left' | 'right'
}

export default function HelpTooltip({ children, content, position = 'top' }: HelpTooltipProps) {
    const { isHelpModeActive } = useHelp()
    const [isVisible, setIsVisible] = useState(false)

    if (!isHelpModeActive) return <>{children}</>

    const positionClasses = {
        top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
        bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
        left: 'right-full top-1/2 -translate-y-1/2 mr-2',
        right: 'left-full top-1/2 -translate-y-1/2 ml-2'
    }

    return (
        <div 
            className="relative inline-block group"
            onMouseEnter={() => setIsVisible(true)}
            onMouseLeave={() => setIsVisible(false)}
        >
            <div className="ring-2 ring-indigo-500/50 rounded-lg transition-all duration-300">
                {children}
            </div>
            
            {isVisible && (
                <div className={`absolute ${positionClasses[position]} z-[10000] w-64 p-3 bg-slate-800 border border-indigo-500/30 rounded-xl shadow-2xl text-xs text-slate-200 leading-relaxed animate-in fade-in zoom-in duration-200`}>
                    <div className="flex items-start gap-2">
                        <span className="text-indigo-400 font-bold shrink-0">⁉️</span>
                        <p>{content}</p>
                    </div>
                    {/* Arrow */}
                    <div className={`absolute w-2 h-2 bg-slate-800 border-b border-r border-indigo-500/30 rotate-45 ${
                        position === 'top' ? 'bottom-[-5px] left-1/2 -translate-x-1/2 border-t-0 border-l-0' :
                        position === 'bottom' ? 'top-[-5px] left-1/2 -translate-x-1/2 border-b-0 border-r-0 rotate-[225deg]' :
                        position === 'left' ? 'right-[-5px] top-1/2 -translate-y-1/2 border-t-0 border-r-0 rotate-[-45deg]' :
                        'left-[-5px] top-1/2 -translate-y-1/2 border-b-0 border-l-0 rotate-[135deg]'
                    }`} />
                </div>
            )}
        </div>
    )
}
