import React from 'react';
import { render } from '@testing-library/react';
import { MathRenderer, renderTextWithMath } from '../MathRenderer';
import '@testing-library/jest-dom';

describe('MathRenderer', () => {
    it('deve renderizar sem quebrar', () => {
        const { container } = render(<MathRenderer formula="a^2 + b^2 = c^2" />);
        expect(container).toBeInTheDocument();
    });

    it('deve converter texto com $ formulas corretamente', () => {
        const text = 'Texto $E=mc^2$ inline';
        const nodes = renderTextWithMath(text);
        expect(nodes).toHaveLength(3); // 'Texto ', math node, ' inline'
    });
});
