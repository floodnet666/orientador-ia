# Metodologia Global: XP + TDD

## OBRIGATÓRIO em toda tarefa de desenvolvimento

### TDD — Test-Driven Development
- **RED → GREEN → REFACTOR** é inegociável
  1. Escreva o teste que falha PRIMEIRO
  2. Implemente o mínimo de código para passar
  3. Refatore mantendo todos os testes verdes
- NUNCA escreva código de produção sem um teste falhando antes
- Cobertura mínima: 80% (linhas e branches)

### XP Practices
- **Pair Programming simulado**: antes de implementar, explique a solução em voz alta (comentário)
- **Small releases**: commits atômicos por funcionalidade mínima testável
- **Refactoring contínuo**: sem "deixar pra depois"
- **Simple design**: YAGNI + KISS — não implemente o que não foi pedido
- **Collective ownership**: todo código deve ser legível por qualquer dev do time
- **Continuous integration**: rode todos os testes antes de cada commit

### Checklist obrigatório por tarefa
- [ ] Testes escritos antes do código de produção
- [ ] Todos os testes passam
- [ ] Sem duplicação de código (DRY)
- [ ] Nomes claros e expressivos
- [ ] Sem comentários óbvios — código deve se autoexplicar
