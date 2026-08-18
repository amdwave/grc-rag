# Eval report - EU AI Act + GDPR


| metric | result |
| --- | --- |
| retrieval hit rate @5 | 27/28 |
| citation correctness | 26/28 |
| refusal correctness | 10/10 |
| verification clean | 35/38 |
| gate floor | 0.595 |

- **q01** (direct): mode `answered`, best dense 0.7167, hit@5 True, citation True, verified True. cited: ai-act#art_51(2), ai-act#rct_111
  - refined id cited (counted as its base chunk): `ai-act#art_51(2)`
- **q02** (direct): mode `answered`, best dense 0.7745, hit@5 True, citation True, verified True. cited: ai-act#art_99(3), ai-act#art_100(2), ai-act#art_5(1)
- **q03** (direct): mode `answered`, best dense 0.7502, hit@5 True, citation True, verified True. cited: ai-act#art_2(1), ai-act#rct_22, ai-act#rct_21, ai-act#art_2(3)
- **q04** (direct): mode `answered`, best dense 0.7638, hit@5 True, citation True, verified True. cited: ai-act#art_50(2), ai-act#rct_133
- **q05** (direct): mode `answered`, best dense 0.7076, hit@5 True, citation True, verified True. cited: ai-act#anx_III(5), ai-act#rct_58
- **q06** (direct): mode `answered`, best dense 0.7855, hit@5 True, citation True, verified True. cited: ai-act#art_49(1), ai-act#art_49(2), ai-act#art_6(4), ai-act#art_49(5), ai-act#art_49(4), ai-act#art_16(i)
  - refined id cited (counted as its base chunk): `ai-act#art_49(1)`
  - refined id cited (counted as its base chunk): `ai-act#art_49(2)`
  - refined id cited (counted as its base chunk): `ai-act#art_49(5)`
  - refined id cited (counted as its base chunk): `ai-act#art_49(4)`
  - refined id cited (counted as its base chunk): `ai-act#art_16(i)`
- **q07** (relocated): mode `answered`, best dense 0.8020, hit@5 True, citation True, verified True. cited: ai-act#art_4a(1), ai-act#rct_70
- **q08** (neighbour_adversary): mode `answered`, best dense 0.7383, hit@5 True, citation True, verified True. cited: ai-act#art_14(4)(b), ai-act#art_14(4)(a)–(e), ai-act#art_14(3), ai-act#art_16(a), ai-act#rct_73
  - refined id cited (counted as its base chunk): `ai-act#art_14(4)(b)`
  - refined id cited (counted as its base chunk): `ai-act#art_14(4)(a)–(e)`
  - refined id cited (counted as its base chunk): `ai-act#art_16(a)`
- **q09** (neighbour_adversary): mode `answered`, best dense 0.7454, hit@5 True, citation True, verified True. cited: ai-act#art_15(5), ai-act#rct_76, ai-act#art_15(4)
- **q10** (neighbour_adversary): mode `answered`, best dense 0.6264, hit@5 True, citation True, verified True. cited: ai-act#art_14(5), ai-act#rct_73
- **q11** (neighbour_adversary): mode `answered`, best dense 0.7693, hit@5 True, citation True, verified True. cited: ai-act#art_6(3), ai-act#art_6(6)
- **q12** (recital): mode `answered`, best dense 0.6945, hit@5 True, citation True, verified True. cited: ai-act#rct_24, ai-act#art_2(3)
- **q13** (recital): mode `answered`, best dense 0.6664, hit@5 True, citation True, verified True. cited: ai-act#rct_12, ai-act#art_3(1)
- **q14** (recital): mode `answered`, best dense 0.7212, hit@5 True, citation True, verified True. cited: ai-act#rct_112, ai-act#art_52(1)
- **q15** (repealed): mode `refused-generation`, best dense 0.6379, refusal True, verified True. cited: -
- **q16** (repealed): mode `refused-generation`, best dense 0.6967, refusal True, verified True. cited: ai-act#anx_I_sct_A(8), ai-act#anx_I_sct_A(9)
- **q17** (unanswerable): mode `refused-gate`, best dense 0.5864, refusal True, verified True. cited: -
- **q18** (unanswerable): mode `refused-gate`, best dense 0.4918, refusal True, verified True. cited: -
- **q19** (direct): mode `answered`, best dense 0.7770, hit@5 True, citation True, verified True. cited: gdpr#art_37(1)(a), gdpr#rct_97, gdpr#art_37(1)(b), gdpr#art_37(1)(c), gdpr#art_37(4), gdpr#art_37(5)
  - refined id cited (counted as its base chunk): `gdpr#art_37(1)(a)`
  - refined id cited (counted as its base chunk): `gdpr#art_37(1)(b)`
  - refined id cited (counted as its base chunk): `gdpr#art_37(1)(c)`
  - refined id cited (counted as its base chunk): `gdpr#art_37(4)`
  - refined id cited (counted as its base chunk): `gdpr#art_37(5)`
- **q20** (unanswerable): mode `refused-generation`, best dense 0.6151, refusal True, verified True. cited: -
- **q21** (direct): mode `answered`, best dense 0.8040, hit@5 True, citation True, verified True. cited: gdpr#art_33, gdpr#rct_85
- **q22** (direct): mode `answered`, best dense 0.6915, hit@5 False, citation False, verified True. cited: gdpr#rct_40, gdpr#rct_46, gdpr#rct_47, gdpr#rct_50
  - full answer text:

    A company may lawfully process personal data on the basis of consent or another legitimate basis laid down by law, including necessity for compliance with a legal obligation or necessity for the performance of a contract. Specifically, "personal data should be processed on the basis of the consent of the data subject concerned or some other legitimate basis, laid down by law, either in this Regulation or in other Union or Member State law as referred to in this Regulation, including the necessity for compliance with the legal obligation to which the controller is subject or the necessity for the performance of a contract to which the data subject is party or in order to take steps at the request of the data subject prior to entering into a contract" [gdpr#rct_40]. Additionally, processing may be lawful where necessary to protect an interest essential for the life of the data subject or another person: "The processing of personal data should also be regarded to be lawful where it is necessary to protect an interest which is essential for the life of the data subject or that of another natural person" [gdpr#rct_46]. Processing may also be based on the legitimate interests of the controller or a third party, provided the data subject's interests or fundamental rights do not override them: "The legitimate interests of a controller, including those of a controller to which the personal data may be disclosed, or of a third party, may provide a legal basis for processing, provided that the interests or the fundamental rights and freedoms of the data subject are not overriding" [gdpr#rct_47]. This basis does not apply to public authorities performing their tasks [gdpr#rct_47]. Further processing for purposes other than the initial collection is allowed where compatible with the original purposes, in which case "no legal basis separate from that which allowed the collection of the personal data is required" [gdpr#rct_50]. Compatibility is assessed considering the link between purposes, context of collection, data subject expectations, nature of the data, consequences, and safeguards [gdpr#rct_50]. Further processing for archiving, scientific or historical research, or statistical purposes is considered compatible [gdpr#rct_50]. Where consent is given or processing is based on Union or Member State law constituting a necessary and proportionate measure to safeguard important objectives of general public interest, further processing is allowed "irrespective of the compatibility of the purposes" [gdpr#rct_50].

- **q23** (direct): mode `answered`, best dense 0.7201, hit@5 True, citation True, verified True. cited: gdpr#art_83(5), gdpr#art_7
- **q24** (direct): mode `answered`, best dense 0.7291, hit@5 True, citation True, verified True. cited: gdpr#art_35(1), gdpr#rct_91, gdpr#art_35(10), gdpr#rct_90, gdpr#art_36(1)
- **q25** (direct): mode `answered`, best dense 0.7140, hit@5 True, citation True, verified True. cited: gdpr#art_44, gdpr#rct_101, gdpr#art_49(1), gdpr#art_46(1), gdpr#rct_115
- **q26** (neighbour_adversary): mode `answered`, best dense 0.6706, hit@5 True, citation True, verified True. cited: gdpr#art_18, gdpr#art_16, gdpr#art_13(2)
- **q27** (neighbour_adversary): mode `answered`, best dense 0.6558, hit@5 True, citation True, verified True. cited: gdpr#art_34(1), gdpr#art_34(2), gdpr#rct_86, gdpr#art_34(3), gdpr#art_34(3)(a), gdpr#art_34(3)(b), gdpr#art_34(3)(c), gdpr#art_34(4)
  - refined id cited (counted as its base chunk): `gdpr#art_34(1)`
  - refined id cited (counted as its base chunk): `gdpr#art_34(2)`
  - refined id cited (counted as its base chunk): `gdpr#art_34(3)`
  - refined id cited (counted as its base chunk): `gdpr#art_34(3)(a)`
  - refined id cited (counted as its base chunk): `gdpr#art_34(3)(b)`
  - refined id cited (counted as its base chunk): `gdpr#art_34(3)(c)`
  - refined id cited (counted as its base chunk): `gdpr#art_34(4)`
- **q28** (neighbour_adversary): mode `answered`, best dense 0.6039, hit@5 True, citation True, verified False. cited: gdpr#art_20, gdpr#rct_68, ai-act#art_50(2)
  - unverified quote (full span): “should not apply where the processing of the personal data is necessary for compliance with a legal obligation... or for the performance of a task carried out in the public interest or in the exercise of an official authority vested in the controller.”
  - full answer text:

    Yes. Under the GDPR, a data subject can require you to hand over the personal data they provided to you in a structured, commonly used and machine-readable format so they can transmit it to another controller (e.g., a competitor), provided the conditions are met. **The right and its conditions** Article 20(1) states: "The data subject shall have the right to receive the personal data concerning him or her, which he or she has provided to a controller, in a structured, commonly used and machine-readable format and have the right to transmit those data to another controller without hindrance from the controller to which the personal data have been provided, where: (a) the processing is based on consent pursuant to point (a) of Article 6(1) or point (a) of Article 9(2) or on a contract pursuant to point (b) of Article 6(1); and (b) the processing is carried out by automated means." [gdpr#art_20] Recital (68) confirms the purpose: "the data subject should also be allowed to receive personal data concerning him or her which he or she has provided to a controller in a structured, commonly used, machine-readable and interoperable format, and to transmit it to another controller." [gdpr#rct_68] **Direct transmission** Article 20(2) adds: "In exercising his or her right to data portability pursuant to paragraph 1, the data subject shall have the right to have the personal data transmitted directly from one controller to another, where technically feasible." [gdpr#art_20] Recital (68) similarly notes: "Where technically feasible, the data subject should have the right to have the personal data transmitted directly from one controller to another." [gdpr#rct_68] **Limitations** - The right does not apply where processing is necessary for a task carried out in the public interest or in the exercise of official authority (Article 20(3)) [gdpr#art_20]; Recital (68) adds it "should not apply where the processing of the personal data is necessary for compliance with a legal obligation... or for the performance of a task carried out in the public interest or in the exercise of an official authority vested in the controller." [gdpr#rct_68] - The right must not "adversely affect the rights and freedoms of others" (Article 20(4)) [gdpr#art_20]; Recital (68) notes that where more than one data subject is concerned, the right is "without prejudice to the rights and freedoms of other data subjects." [gdpr#rct_68] - The right is "without prejudice to Article 17" (the right to erasure) [gdpr#art_20]; Recital (68) clarifies it "should not prejudice the right of the data subject to obtain the erasure of personal data." [gdpr#rct_68] - Recital (68) also states the right "should not create an obligation for the controllers to adopt or maintain processing systems which are technically compatible." [gdpr#rct_68] **Note on AI-generated content (not applicable to your question)** The AI Act's Article 50(2) requires providers of AI systems generating synthetic content to mark outputs as artificially generated in a machine-readable format [ai-act#art_50(2)], but this is a separate transparency obligation for AI providers, not a data portability right.

- **q29** (recital): mode `refused-generation`, best dense 0.6064, hit@5 True, citation False, verified True. cited: gdpr#rct_47, gdpr#rct_50
  - full answer text:

    The corpus does not address this. The retrieved documents discuss the role of "reasonable expectations" in the legitimate-interests assessment [gdpr#rct_47] and in the compatibility of further processing [gdpr#rct_50], but they do not explain the underlying rationale for why reliance on legitimate interests depends on those expectations.

- **q30** (recital): mode `answered`, best dense 0.6672, hit@5 True, citation True, verified False. cited: gdpr#rct_26, gdpr#art_4(5), gdpr#art_11(1), gdpr#art_11(2)
  - refined id cited (counted as its base chunk): `gdpr#art_11(1)`
  - refined id cited (counted as its base chunk): `gdpr#art_11(2)`
  - unverified quote (full span): “not obliged to maintain, acquire or process additional information in order to identify the data subject for the sole purpose of complying with this Regulation.”
  - full answer text:

    Based on the provided documents, the GDPR stops treating information as personal data when it is anonymous, meaning the data subject is not or no longer identifiable. This is distinct from pseudonymised data, which remains personal data. The decisive language is in Recital 26: "The principles of data protection should therefore not apply to anonymous information, namely information which does not relate to an identified or identifiable natural person or to personal data rendered anonymous in such a manner that the data subject is not or no longer identifiable." [gdpr#rct_26] To determine whether a person is identifiable, the same Recital states that "account should be taken of all the means reasonably likely to be used, such as singling out, either by the controller or by another person to identify the natural person directly or indirectly," and that "account should be taken of all objective factors, such as the costs of and the amount of time required for identification, taking into consideration the available technology at the time of the processing and technological developments." [gdpr#rct_26] In contrast, pseudonymised data is still treated as personal data. Recital 26 states that "Personal data which have undergone pseudonymisation, which could be attributed to a natural person by the use of additional information should be considered to be information on an identifiable natural person." [gdpr#rct_26] The definition of pseudonymisation in Article 4(5) confirms this, as it describes processing that makes data "no longer be attributed to a specific data subject without the use of additional information," which is kept separately. [gdpr#art_4(5)] Additionally, Article 11 provides a related but distinct rule: if the controller no longer requires identification of the data subject for its purposes, it is "not obliged to maintain, acquire or process additional information in order to identify the data subject for the sole purpose of complying with this Regulation." [gdpr#art_11(1)] In such cases, if the controller can demonstrate it is not in a position to identify the data subject, it must inform the data subject, and Articles 15 to 20 (data subject rights) do not apply unless the data subject provides additional identifying information. [gdpr#art_11(2)]

- **q31** (cross_instrument): mode `answered`, best dense 0.6765, hit@5 True, citation True, verified True. cited: gdpr#art_22, gdpr#rct_71, gdpr#art_21, ai-act#rct_171, ai-act#rct_10
- **q32** (cross_instrument): mode `answered`, best dense 0.7530, hit@5 True, citation True, verified True. cited: ai-act#art_27(1), ai-act#rct_96, ai-act#art_27(2)
- **q33** (cross_instrument): mode `answered`, best dense 0.7106, hit@5 True, citation True, verified True. cited: gdpr#art_15(1), gdpr#art_15(3), gdpr#rct_60
- **q34** (unanswerable): mode `refused-gate`, best dense 0.5656, refusal True, verified True. cited: -
- **q35** (unanswerable): mode `refused-gate`, best dense 0.5853, refusal True, verified True. cited: -
- **q36** (unanswerable): mode `refused-generation`, best dense 0.6413, refusal True, verified True. cited: -
- **q37** (unanswerable): mode `refused-generation`, best dense 0.6135, refusal True, verified False. cited: gdpr#art_30(1), gdpr#art_32, ai-act#art_31(2), ai-act#anx_VII(4), ai-act#art_17(1)
  - unverified quote (full span): “Statement of Applicability”
  - unverified quote (full span): “information security management system.”
  - full answer text:

    The corpus does not address this. The retrieved documents concern GDPR record-keeping requirements [gdpr#art_30(1)], GDPR security measures [gdpr#art_32], and EU AI Act provisions on notified bodies and quality management systems [ai-act#art_31(2)], [ai-act#anx_VII(4)], [ai-act#art_17(1)], but none of them mention a "Statement of Applicability" or an "information security management system."

- **q38** (unanswerable): mode `refused-generation`, best dense 0.6210, refusal True, verified True. cited: gdpr#art_33
