# Eval report - EU AI Act (M4)


| metric | result |
| --- | --- |
| retrieval hit rate @5 | 14/14 |
| citation correctness | 14/14 |
| refusal correctness | 6/6 |
| verification clean | 19/20 |
| gate floor | 0.62 |

- **q01** (direct): mode `answered`, best dense 0.7167, hit@5 True, citation True, verified True. cited: ai-act#art_51(2), ai-act#rct_111
  - refined id cited (counted as its base chunk): `ai-act#art_51(2)`
- **q02** (direct): mode `answered`, best dense 0.7745, hit@5 True, citation True, verified True. cited: ai-act#art_99(3), ai-act#art_100(2)
- **q03** (direct): mode `answered`, best dense 0.7502, hit@5 True, citation True, verified True. cited: ai-act#art_2(1), ai-act#rct_22, ai-act#rct_21, ai-act#art_2(3)
- **q04** (direct): mode `answered`, best dense 0.7638, hit@5 True, citation True, verified True. cited: ai-act#art_50(2), ai-act#rct_133
- **q05** (direct): mode `answered`, best dense 0.7076, hit@5 True, citation True, verified True. cited: ai-act#anx_III(5), ai-act#rct_58
- **q06** (direct): mode `answered`, best dense 0.7855, hit@5 True, citation True, verified True. cited: ai-act#art_49
- **q07** (relocated): mode `answered`, best dense 0.8020, hit@5 True, citation True, verified True. cited: ai-act#art_4a(1), ai-act#rct_70
- **q08** (neighbour_adversary): mode `answered`, best dense 0.7383, hit@5 True, citation True, verified True. cited: ai-act#art_14(4), ai-act#art_14(3), ai-act#art_16, ai-act#rct_73
- **q09** (neighbour_adversary): mode `answered`, best dense 0.7454, hit@5 True, citation True, verified False. cited: ai-act#art_15(5), ai-act#rct_76
  - unverified quote (full span): “The technical solutions to address AI specific vulnerabilities shall include, where appropriate, measures to prevent, detect, respond to, resolve and control for attacks trying to manipulate the training data set (data poisoning)... inputs designed to cause the AI model to make a mistake (adversarial examples or model evasion)”
  - full answer text:

    High-risk AI systems must be resilient against attempts by unauthorised third parties to alter their use, outputs or performance by exploiting system vulnerabilities, and the technical solutions must include measures to prevent, detect, respond to, resolve and control for attacks trying to manipulate the training data set (data poisoning) or inputs designed to cause the AI model to make a mistake (adversarial examples or model evasion) [ai-act#art_15(5)]. The decisive language is: "High-risk AI systems shall be resilient against attempts by unauthorised third parties to alter their use, outputs or performance by exploiting system vulnerabilities" and "The technical solutions to address AI specific vulnerabilities shall include, where appropriate, measures to prevent, detect, respond to, resolve and control for attacks trying to manipulate the training data set (data poisoning)... inputs designed to cause the AI model to make a mistake (adversarial examples or model evasion)" [ai-act#art_15(5)]. Additionally, Recital (76) confirms that cybersecurity is crucial for resilience against such attacks, noting that "Cyberattacks against AI systems can leverage AI specific assets, such as training data sets (e.g. data poisoning) or trained models (e.g. adversarial attacks or membership inference)" and that providers should take "suitable measures, such as security controls" appropriate to the risks [ai-act#rct_76].

- **q10** (neighbour_adversary): mode `answered`, best dense 0.6264, hit@5 True, citation True, verified True. cited: ai-act#art_14(5), ai-act#rct_73
- **q11** (neighbour_adversary): mode `answered`, best dense 0.7693, hit@5 True, citation True, verified True. cited: ai-act#art_6(3), ai-act#art_6(6), ai-act#art_7(3)
- **q12** (recital): mode `answered`, best dense 0.6945, hit@5 True, citation True, verified True. cited: ai-act#rct_24, ai-act#art_2(3)
- **q13** (recital): mode `answered`, best dense 0.6664, hit@5 True, citation True, verified True. cited: ai-act#rct_12, ai-act#art_3(1)
- **q14** (recital): mode `answered`, best dense 0.7212, hit@5 True, citation True, verified True. cited: ai-act#rct_112, ai-act#art_52(1)
- **q15** (repealed): mode `refused-generation`, best dense 0.6379, refusal True, verified True. cited: -
- **q16** (repealed): mode `refused-generation`, best dense 0.6967, refusal True, verified True. cited: -
- **q17** (unanswerable): mode `refused-gate`, best dense 0.5864, refusal True, verified True. cited: -
- **q18** (unanswerable): mode `refused-gate`, best dense 0.4918, refusal True, verified True. cited: -
- **q19** (unanswerable): mode `refused-gate`, best dense 0.5669, refusal True, verified True. cited: -
- **q20** (unanswerable): mode `refused-gate`, best dense 0.6151, refusal True, verified True. cited: -
