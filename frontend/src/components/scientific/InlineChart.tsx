import React from 'react';
import {
    LineChart, Line, BarChart, Bar,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';

export type ChartType = 'line' | 'bar';

export interface ChartConfig {
    type: ChartType;
    data: Array<Record<string, string | number>>;
    xKey: string;
    yKeys: string[];
    title?: string;
    colors?: string[];
}

const DEFAULT_COLORS = ['#38bdf8', '#f59e0b', '#34d399', '#fb7185', '#818cf8'];

export function InlineChart({ type, data, xKey, yKeys, title, colors = DEFAULT_COLORS }: ChartConfig) {
    const ChartComponent = type === 'bar' ? BarChart : LineChart;
    const DataComponent  = type === 'bar' ? Bar : Line;

    return (
        <div style={{ width: '100%', marginBottom: 16 }}>
            {title && (
                <p style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: 11,
                            color: 'var(--text-muted, #888)', marginBottom: 8, textTransform: 'uppercase' }}>
                    {title}
                </p>
            )}
            <ResponsiveContainer width="100%" height={200}>
                <ChartComponent data={data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: '#556678' }} />
                    <YAxis tick={{ fontSize: 11, fill: '#556678' }} />
                    <Tooltip
                        contentStyle={{ background: '#121f35', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 6 }}
                        labelStyle={{ color: '#f0ead6' }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    {yKeys.map((key, i) => (
                        <DataComponent
                            key={key}
                            type="monotone"
                            dataKey={key}
                            stroke={colors[i % colors.length]}
                            fill={colors[i % colors.length]}
                            strokeWidth={2}
                            dot={false}
                        />
                    ))}
                </ChartComponent>
            </ResponsiveContainer>
        </div>
    );
}
