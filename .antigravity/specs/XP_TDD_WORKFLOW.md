# Workflow XP+TDD para todos os agentes

## Sequência obrigatória ao receber qualquer task de código:

1. **Análise**: Entenda o requisito. Faça perguntas se ambíguo.
2. **Design mínimo**: Esboce a interface pública (não a implementação)
3. **RED**: Escreva testes unitários que descrevem o comportamento esperado
4. **GREEN**: Implemente o código mais simples possível para passar
5. **REFACTOR**: Melhore sem quebrar testes
6. **Integration test**: Adicione teste de integração se aplicável
7. **Commit**: Mensagem descritiva no formato `feat/fix/refactor: descrição`

## Nunca faça:
- Implementar antes de testar
- Commit com testes falhando
- Classes/funções com mais de uma responsabilidade
- Métodos com mais de 20 linhas sem refatorar
