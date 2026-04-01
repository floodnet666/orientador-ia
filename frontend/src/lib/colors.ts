export const ALMA_COLORS = [
    { name: 'Red', hex: '#ef4444', emoji: '🔴', border: 'border-red-500', text: 'text-red-500', bg: 'bg-red-500/10' },
    { name: 'Orange', hex: '#f97316', emoji: '🟠', border: 'border-orange-500', text: 'text-orange-500', bg: 'bg-orange-500/10' },
    { name: 'Yellow', hex: '#eab308', emoji: '🟡', border: 'border-yellow-500', text: 'text-yellow-500', bg: 'bg-yellow-500/10' },
    { name: 'Green', hex: '#22c55e', emoji: '🟢', border: 'border-green-500', text: 'text-green-500', bg: 'bg-green-500/10' },
    { name: 'Blue', hex: '#3b82f6', emoji: '🔵', border: 'border-blue-500', text: 'text-blue-500', bg: 'bg-blue-500/10' },
    { name: 'Purple', hex: '#a855f7', emoji: '🟣', border: 'border-purple-500', text: 'text-purple-500', bg: 'bg-purple-500/10' },
];

export function getAlmaMetadata(almaIdOrName: string | null | undefined, activeAlmas: any[]) {
    if (!almaIdOrName) return null;
    
    // Find index in active almas
    const index = activeAlmas.findIndex(a => 
        a.id === almaIdOrName || a.name === almaIdOrName || a.alma_name === almaIdOrName
    );
    
    if (index === -1) return null;
    
    const color = ALMA_COLORS[index % ALMA_COLORS.length];
    return {
        ...color,
        index
    };
}
