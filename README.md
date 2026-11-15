# Zvtakum — Extensão vetorial RISC-V (RVV) com o formato Takum

Simulador em Python da extensão **Zvtakum** (`vtadd.vv`, `vtsub.vv`, `vtmul.vv`,
`vtdot8/16/32.vv`, `vncvt.t.t`) e experimento que compara o erro de `y = A · x`
em Takum (T8/T16/T32) contra o padrão IEEE (FP8/FP16/FP32).

## Requisitos

- Python 3.10 ou superior 
- `numpy` e `matplotlib` 

```bash
pip install numpy matplotlib
```

## Estrutura

| Arquivo | Função |
|---|---|
| `takum.py` | Codificação/decodificação do Takum logarítmico e conversão float ↔ Takum |
| `calculos.py` | Conversões de largura, produto escalar e ULA: soma, subtração, multiplicação |
| `estruturas.py` | Registradores, memória, PC e CSRs vetoriais (VLEN = 128) |
| `codificacao.py` | Montador e unidade de controle (palavra de 32 bits ↔ instrução) |
| `instrucoes.py` | Executor de cada instrução |
| `main.py` | Ciclo buscar → decodificar → executar |
| `testes_manuais.py` | Testes feitos para análise visual |
| `testes_automaticos.py` | Os mesmos testes de testes_manuais, porém com asserts (`unittest`) |
| `experimennto.py` | Experimento `y = A · x` (Takum × IEEE) |
| `graficos.py` | Gráficos por tamanho de matriz e violin plot |



## Como executar os testes

Os comandos a seguir devem ser executados a partir da pasta `src`

### Testes automáticos

```bash
python -m unittest testes_automaticos -v
```

A saída termina com `OK` quando tudo passa. Para rodar só uma classe ou um teste:

```bash
python -m unittest testes_automaticos.TestVncvtDot
python -m unittest testes_automaticos.TestVncvtDot.test_vtdot8
```

Os valores em Takum são aproximados, então os testes comparam com tolerância
relativa em vez de igualdade exata.

### Testes manuais (`testes_manuais.py`)

```bash
python testes_manuais.py
```

Este script só imprime resultados (memória antes/depois, registradores, bits)
para conferência visual. Não falha sozinho se algo estiver errado. Para isso
use os testes automáticos.

## Como executar o experimento

O experimento gera dados com semente fixa (`SEMENTE = 42`), roda o produto
matriz-vetor no simulador (Takum) e em Python (IEEE), e mede o erro relativo
contra uma referência em `Decimal` com 34 dígitos.

### Executando

```bash
python experimennto.py
```

Na configuração atual, demonstracao executa a multiplicação de uma matriz 6x6 por um vetor e mostra como é feita a separação por lane, como esses dados são armazenados na memoria e o resultado da operação. A demonstração também calcula o erro e faz uma comparação entre os formatos Takum e IEEE.


O experimento também é responsavel por imprimir o progresso e salva quatro imagens na pasta atual:

- `mediana.png`: mediana do erro relativo por tamanho de matriz
- `media.png`: média do erro relativo por tamanho de matriz
- `violino.png`: distribuição do erro relativo (matriz 100×100)
- `escalar.png`: mediana do erro relativo por faixa de escala



## Executar uma instrução ou programa isolado

```python
from estruturas import Maquina
from codificacao import montar
from main import executar

m = Maquina()
m.carregar_programa(montar([
    "li t1, 4",
    "vsetvli t0, t1, e16, m1, ta, ma",
    "vle16.v v1, (a0)",
    "vle16.v v2, (a1)",
    "vtadd.vv v3, v1, v2",
    "vse16.v v3, (a2)",
]))
# antes: escreva os dados na memória e os endereços em a0, a1, a2
executar(m)
```

`python main.py` imprime a codificação de exemplo de `vtmul.vv v1, v2, v3`
(`0x922190AB`).