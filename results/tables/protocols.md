# Validation protocols (RQ2)

Shipped choice rule unless the rule column says otherwise. Validated recall is on the protocol's own report set; A3 seed 37 is the secondary target (the report set itself for P4); X2, the primary target, is not tested yet. MAE: mean over checks of the absolute recall error on A3 seed 37.

| Fold | Rule | required_field crowned | Validated recall (required_field) | A3 seed 37 recall (required_field) | Gate 0.90 blocks | MAE on A3 seed 37 |
|---|---|---|---|---|---|---|
| P1 | B1 | `text_sensor=ink, ink_threshold=190` | 1.000 (936/936) | 0.577 (270/468) | no | 0.226 |
| P1 | B2 | `text_sensor=ink, ink_threshold=190` | 1.000 (936/936) | 0.590 (276/468) | no | 0.235 |
| P1 | B3_and | `text_sensor=ink, ink_threshold=190` AND `text_sensor=zone, min_conf=0.0` | 0.923 (864/936) | 0.564 (264/468) | | |
| P1 | B3_or | `text_sensor=ink, ink_threshold=190` OR `text_sensor=zone, min_conf=0.0` | 1.000 (936/936) | 0.682 (319/468) | | |
| P1 | budget_0.001 | `text_sensor=ink, ink_threshold=190` | 1.000 (936/936) | 0.577 (270/468) | no | 0.226 |
| P1 | budget_0.005 | `text_sensor=ink, ink_threshold=190` | 1.000 (936/936) | 0.577 (270/468) | no | 0.226 |
| P1 | shipped | `text_sensor=ink, ink_threshold=190` | 1.000 (936/936) | 0.577 (270/468) | no | 0.226 |
| P2 | B1 | `text_sensor=ink, ink_threshold=190` | 1.000 (936/936) | 0.590 (276/468) | no | 0.183 |
| P2 | B2 | `text_sensor=ink, ink_threshold=190` | 1.000 (936/936) | 0.592 (277/468) | no | 0.200 |
| P2 | B3_and | `text_sensor=ink, ink_threshold=128` AND `text_sensor=page, min_conf=0.0` | 0.000 (0/936) | 0.000 (0/468) | | |
| P2 | B3_or | `text_sensor=ink, ink_threshold=128` OR `text_sensor=page, min_conf=0.0` | 0.795 (744/936) | 0.588 (275/468) | | |
| P2 | budget_0.001 | `text_sensor=ink, ink_threshold=128` | 0.795 (744/936) | 0.588 (275/468) | yes | 0.158 |
| P2 | budget_0.005 | `text_sensor=ink, ink_threshold=128` | 0.795 (744/936) | 0.588 (275/468) | yes | 0.165 |
| P2 | shipped | `text_sensor=ink, ink_threshold=128` | 0.795 (744/936) | 0.588 (275/468) | yes | 0.158 |
| P3/angle=2.0 | B1 | `text_sensor=ink, ink_threshold=190` | 1.000 (936/936) | 0.577 (270/468) | no | 0.226 |
| P3/angle=2.0 | B2 | `text_sensor=ink, ink_threshold=190` | 1.000 (936/936) | 0.590 (276/468) | no | 0.235 |
| P3/angle=2.0 | B3_and | `text_sensor=ink, ink_threshold=190` AND `text_sensor=zone, min_conf=0.0` | 0.923 (864/936) | 0.564 (264/468) | | |
| P3/angle=2.0 | B3_or | `text_sensor=ink, ink_threshold=190` OR `text_sensor=zone, min_conf=0.0` | 1.000 (936/936) | 0.682 (319/468) | | |
| P3/angle=2.0 | budget_0.001 | `text_sensor=ink, ink_threshold=190` | 1.000 (936/936) | 0.577 (270/468) | no | 0.240 |
| P3/angle=2.0 | budget_0.005 | `text_sensor=ink, ink_threshold=190` | 1.000 (936/936) | 0.577 (270/468) | no | 0.240 |
| P3/angle=2.0 | shipped | `text_sensor=ink, ink_threshold=190` | 1.000 (936/936) | 0.577 (270/468) | no | 0.240 |
| P3/dpi=150 | B1 | `text_sensor=ink, ink_threshold=190` | n/a (0/0) | 0.577 (270/468) | no | n/a |
| P3/dpi=150 | B2 | `text_sensor=ink, ink_threshold=190` | n/a (0/0) | 0.590 (276/468) | no | n/a |
| P3/dpi=150 | B3_and | `text_sensor=ink, ink_threshold=190` AND `text_sensor=zone, min_conf=0.0` | n/a (0/0) | 0.564 (264/468) | | |
| P3/dpi=150 | B3_or | `text_sensor=ink, ink_threshold=190` OR `text_sensor=zone, min_conf=0.0` | n/a (0/0) | 0.682 (319/468) | | |
| P3/dpi=150 | budget_0.001 | `text_sensor=ink, ink_threshold=190` | n/a (0/0) | 0.577 (270/468) | no | n/a |
| P3/dpi=150 | budget_0.005 | `text_sensor=ink, ink_threshold=190` | n/a (0/0) | 0.577 (270/468) | no | n/a |
| P3/dpi=150 | shipped | `text_sensor=ink, ink_threshold=190` | n/a (0/0) | 0.577 (270/468) | no | n/a |
| P3/sigma=6.0 | B1 | `text_sensor=ink, ink_threshold=190` | 1.000 (1404/1404) | 0.577 (270/468) | no | 0.236 |
| P3/sigma=6.0 | B2 | `text_sensor=ink, ink_threshold=190` | 1.000 (1404/1404) | 0.590 (276/468) | no | 0.231 |
| P3/sigma=6.0 | B3_and | `text_sensor=ink, ink_threshold=190` AND `text_sensor=union, min_conf=0.0` | 0.831 (1167/1404) | 0.511 (239/468) | | |
| P3/sigma=6.0 | B3_or | `text_sensor=ink, ink_threshold=190` OR `text_sensor=union, min_conf=0.0` | 1.000 (1404/1404) | 0.658 (308/468) | | |
| P3/sigma=6.0 | budget_0.001 | `text_sensor=ink, ink_threshold=190` | 1.000 (1404/1404) | 0.577 (270/468) | no | 0.236 |
| P3/sigma=6.0 | budget_0.005 | `text_sensor=ink, ink_threshold=190` | 1.000 (1404/1404) | 0.577 (270/468) | no | 0.236 |
| P3/sigma=6.0 | shipped | `text_sensor=ink, ink_threshold=190` | 1.000 (1404/1404) | 0.577 (270/468) | no | 0.236 |
| P4 | B1 | `text_sensor=ink, ink_threshold=190` | 0.962 (150/156) | 0.577 (270/468) | no | 0.159 |
| P4 | B2 | `text_sensor=ink, ink_threshold=190` | 1.000 (156/156) | 0.590 (276/468) | no | 0.173 |
| P4 | B3_and | `text_sensor=ink, ink_threshold=190` AND `text_sensor=zone, min_conf=0.0` | 0.923 (144/156) | 0.564 (264/468) | | |
| P4 | B3_or | `text_sensor=ink, ink_threshold=190` OR `text_sensor=zone, min_conf=0.0` | 1.000 (156/156) | 0.682 (319/468) | | |
| P4 | budget_0.001 | `text_sensor=ink, ink_threshold=190` | 0.962 (150/156) | 0.577 (270/468) | no | 0.159 |
| P4 | budget_0.005 | `text_sensor=ink, ink_threshold=190` | 0.962 (150/156) | 0.577 (270/468) | no | 0.159 |
| P4 | shipped | `text_sensor=ink, ink_threshold=190` | 0.962 (150/156) | 0.577 (270/468) | no | 0.159 |
| P5 | B1 | `text_sensor=ink, ink_threshold=190` | 0.921 (3018/3276) | 0.590 (276/468) | no | 0.185 |
| P5 | B2 | `text_sensor=ink, ink_threshold=128` | 0.890 (2916/3276) | 0.615 (288/468) | yes | 0.190 |
| P5 | B3_and | `text_sensor=ink, ink_threshold=160` AND `text_sensor=page, min_conf=0.0` | 0.000 (0/3276) | 0.000 (0/468) | | |
| P5 | B3_or | `text_sensor=ink, ink_threshold=160` OR `text_sensor=page, min_conf=0.0` | 0.000 (0/3276) | 0.000 (0/468) | | |
| P5 | budget_0.001 | `text_sensor=ink, ink_threshold=128` | 0.000 (0/3276) | 0.000 (0/468) | yes | 0.161 |
| P5 | budget_0.005 | `text_sensor=ink, ink_threshold=190` | 0.027 (90/3276) | 0.013 (6/468) | yes | 0.162 |
| P5 | shipped | `text_sensor=ink, ink_threshold=160` | 0.000 (0/3276) | 0.000 (0/468) | yes | 0.151 |
| P6/identity=id01 | B1 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.226 |
| P6/identity=id01 | B2 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.590 (276/468) | no | 0.235 |
| P6/identity=id01 | B3_and | `text_sensor=ink, ink_threshold=190` AND `text_sensor=zone, min_conf=0.0` | 0.923 (432/468) | 0.564 (264/468) | | |
| P6/identity=id01 | B3_or | `text_sensor=ink, ink_threshold=190` OR `text_sensor=zone, min_conf=0.0` | 1.000 (468/468) | 0.682 (319/468) | | |
| P6/identity=id01 | budget_0.001 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.238 |
| P6/identity=id01 | budget_0.005 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.238 |
| P6/identity=id01 | shipped | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.238 |
| P6/identity=id02 | B1 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.226 |
| P6/identity=id02 | B2 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.590 (276/468) | no | 0.235 |
| P6/identity=id02 | B3_and | `text_sensor=ink, ink_threshold=190` AND `text_sensor=zone, min_conf=0.0` | 0.923 (432/468) | 0.564 (264/468) | | |
| P6/identity=id02 | B3_or | `text_sensor=ink, ink_threshold=190` OR `text_sensor=zone, min_conf=0.0` | 1.000 (468/468) | 0.682 (319/468) | | |
| P6/identity=id02 | budget_0.001 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.238 |
| P6/identity=id02 | budget_0.005 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.238 |
| P6/identity=id02 | shipped | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.238 |
| P6/identity=id03 | B1 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.226 |
| P6/identity=id03 | B2 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.590 (276/468) | no | 0.235 |
| P6/identity=id03 | B3_and | `text_sensor=ink, ink_threshold=190` AND `text_sensor=zone, min_conf=0.0` | 0.923 (432/468) | 0.564 (264/468) | | |
| P6/identity=id03 | B3_or | `text_sensor=ink, ink_threshold=190` OR `text_sensor=zone, min_conf=0.0` | 1.000 (468/468) | 0.682 (319/468) | | |
| P6/identity=id03 | budget_0.001 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.238 |
| P6/identity=id03 | budget_0.005 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.238 |
| P6/identity=id03 | shipped | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.238 |
| P6/identity=id04 | B1 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.226 |
| P6/identity=id04 | B2 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.590 (276/468) | no | 0.235 |
| P6/identity=id04 | B3_and | `text_sensor=ink, ink_threshold=190` AND `text_sensor=zone, min_conf=0.0` | 0.923 (432/468) | 0.564 (264/468) | | |
| P6/identity=id04 | B3_or | `text_sensor=ink, ink_threshold=190` OR `text_sensor=zone, min_conf=0.0` | 1.000 (468/468) | 0.682 (319/468) | | |
| P6/identity=id04 | budget_0.001 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.238 |
| P6/identity=id04 | budget_0.005 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.238 |
| P6/identity=id04 | shipped | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.238 |
| P6/identity=id05 | B1 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.226 |
| P6/identity=id05 | B2 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.590 (276/468) | no | 0.235 |
| P6/identity=id05 | B3_and | `text_sensor=ink, ink_threshold=190` AND `text_sensor=zone, min_conf=0.0` | 0.923 (432/468) | 0.564 (264/468) | | |
| P6/identity=id05 | B3_or | `text_sensor=ink, ink_threshold=190` OR `text_sensor=zone, min_conf=0.0` | 1.000 (468/468) | 0.682 (319/468) | | |
| P6/identity=id05 | budget_0.001 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.238 |
| P6/identity=id05 | budget_0.005 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.238 |
| P6/identity=id05 | shipped | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.577 (270/468) | no | 0.238 |
| P6/identity=id06 | B1 | `text_sensor=ink, ink_threshold=190` | 0.994 (465/468) | 0.564 (264/468) | no | 0.227 |
| P6/identity=id06 | B2 | `text_sensor=ink, ink_threshold=190` | 1.000 (468/468) | 0.590 (276/468) | no | 0.235 |
| P6/identity=id06 | B3_and | `text_sensor=ink, ink_threshold=190` AND `text_sensor=zone, min_conf=0.0` | 0.917 (429/468) | 0.551 (258/468) | | |
| P6/identity=id06 | B3_or | `text_sensor=ink, ink_threshold=190` OR `text_sensor=zone, min_conf=0.0` | 1.000 (468/468) | 0.682 (319/468) | | |
| P6/identity=id06 | budget_0.001 | `text_sensor=ink, ink_threshold=190` | 0.994 (465/468) | 0.564 (264/468) | no | 0.239 |
| P6/identity=id06 | budget_0.005 | `text_sensor=ink, ink_threshold=190` | 0.994 (465/468) | 0.564 (264/468) | no | 0.239 |
| P6/identity=id06 | shipped | `text_sensor=ink, ink_threshold=190` | 0.994 (465/468) | 0.564 (264/468) | no | 0.239 |
