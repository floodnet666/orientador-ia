'use client'
import React, { createContext, useContext, useState, useEffect } from 'react'

interface HelpContextType {
    isHelpModeActive: boolean
    toggleHelpMode: () => void
    hasSeenOnboarding: boolean
    completeOnboarding: () => void
}

const HelpContext = createContext<HelpContextType | undefined>(undefined)

export function HelpProvider({ children }: { children: React.ReactNode }) {
    const [isHelpModeActive, setIsHelpModeActive] = useState(false)
    const [hasSeenOnboarding, setHasSeenOnboarding] = useState(true) // Initial true to avoid flash

    useEffect(() => {
        const seen = localStorage.getItem('has_seen_onboarding') === 'true'
        setHasSeenOnboarding(seen)
    }, [])

    const toggleHelpMode = () => setIsHelpModeActive(prev => !prev)

    const completeOnboarding = () => {
        localStorage.setItem('has_seen_onboarding', 'true')
        setHasSeenOnboarding(true)
    }

    return (
        <HelpContext.Provider value={{ isHelpModeActive, toggleHelpMode, hasSeenOnboarding, completeOnboarding }}>
            {children}
            {isHelpModeActive && (
                <div className="fixed bottom-4 right-4 bg-indigo-600 text-white px-4 py-2 rounded-full shadow-lg z-[9999] animate-pulse pointer-events-none">
                    Modo Ajuda Ativo ⁉️
                </div>
            )}
        </HelpContext.Provider>
    )
}

export function useHelp() {
    const context = useContext(HelpContext)
    if (!context) throw new Error('useHelp must be used within HelpProvider')
    return context
}
