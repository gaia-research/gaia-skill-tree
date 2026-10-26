/**
 * synthetic_trust_lifecycle_fixtures.js
 *
 * Deterministic, clearly synthetic test fixture harness for all Yggdrasil IV
 * trust lifecycle and challenge history presentation states.
 *
 * All identifiers and handles use the synthetic prefix to guarantee that NO
 * real skill standing or production data is modified.
 */

'use strict';

var SYNTHETIC_FIXTURES = {
  // State 1: In Good Standing (approved 4★, TM 125, merit Origin held, no active challenges)
  inGoodStanding: {
    id: 'synthetic-author/synthetic-in-good-standing',
    name: 'Synthetic In Good Standing',
    level: '4★',
    trustMagnitude: 125,
    overallTrustGrade: 'A',
    genericSkillRef: 'synthetic-capability-root',
    trustLifecycle: {
      snapshot: {
        snapshotId: 'snap-synthetic-2026-10-26-001',
        evaluatedAtUTC: '2026-10-26T00:00:00Z',
        policyVersion: 'yggdrasil-4.0.0-synthetic',
        approvedBy: 'synthetic-maintainer',
        approvalRef: 'https://github.com/gaia-research/gaia-skill-tree/pull/9999'
      },
      approvedStanding: {
        status: 'in-good-standing',
        approvedStars: 4,
        approvedTm: 125,
        degradation: null,
        recalibrationPending: null
      },
      origin: {
        status: 'held',
        currentOriginHandle: 'synthetic-author',
        contested: false,
        genericSkillRef: 'synthetic-capability-root',
        incumbentNotice: 'Holds merit-based Origin; cannot be transferred or vacated without Class C review.'
      },
      challenges: [],
      historicalAwards: [
        {
          awardType: 'origin-awarded',
          dateUTC: '2026-05-01T00:00:00Z',
          handle: 'synthetic-author',
          stars: 2,
          title: 'Merit-Based Origin Awarded',
          notes: 'Demonstrated initial reference implementation',
          receiptRef: 'https://github.com/gaia-research/gaia-skill-tree/issues/1001'
        },
        {
          awardType: 'rank-awarded',
          dateUTC: '2026-08-15T00:00:00Z',
          handle: 'synthetic-author',
          stars: 4,
          title: '4★ Unique Promotion',
          notes: 'Overall Trust Grade A ratified',
          receiptRef: 'https://github.com/gaia-research/gaia-skill-tree/issues/1002'
        }
      ]
    }
  },

  // State 2: Verified Scoped Capability Challenge (Origin is NOT contested)
  scopedCapabilityChallenge: {
    id: 'synthetic-author/synthetic-scoped-challenge',
    name: 'Synthetic Scoped Challenge',
    level: '4★',
    trustMagnitude: 115,
    overallTrustGrade: 'A',
    genericSkillRef: 'synthetic-capability-root',
    trustLifecycle: {
      snapshot: {
        snapshotId: 'snap-synthetic-2026-10-26-002',
        evaluatedAtUTC: '2026-10-26T00:00:00Z',
        policyVersion: 'yggdrasil-4.0.0-synthetic',
        approvedBy: 'synthetic-maintainer',
        approvalRef: 'https://github.com/gaia-research/gaia-skill-tree/pull/9999'
      },
      approvedStanding: {
        status: 'in-good-standing',
        approvedStars: 4,
        approvedTm: 115
      },
      origin: {
        status: 'held',
        currentOriginHandle: 'synthetic-author',
        contested: false,
        genericSkillRef: 'synthetic-capability-root'
      },
      challenges: [
        {
          challengeId: 'ch-synthetic-scoped-001',
          claimId: 'claim-throughput-01',
          claim: 'Throughput degrades by 45% when token batch size exceeds 128',
          behaviorId: 'batch-throughput',
          materialToOrigin: false, // Scoped capability challenge: does NOT contest Origin!
          scopeDescription: 'Evaluated under Node.js 22 LTS with 256-concurrency load test',
          status: 'verified-pending',
          pinnedVersion: 'v1.4.0',
          pinnedSha: 'a1b2c3d4e5f6',
          environment: 'linux-x64-cgroup-v2',
          comparator: 'synthetic-comparator-fast v2.0',
          baseline: '85 req/s (synthetic-author) vs 155 req/s (comparator)',
          verifiedAtUTC: '2026-10-24T12:00:00Z',
          verifier: {
            verifierId: 'synthetic-independent-verifier',
            verificationMethod: 'reproducible-container-benchmark',
            receiptUrl: 'https://github.com/gaia-research/gaia-skill-tree/issues/9991'
          },
          contributorNoticeRef: 'https://github.com/gaia-research/gaia-skill-tree/issues/9991#notice',
          responseDueUTC: '2026-11-07T12:00:00Z'
        }
      ],
      historicalAwards: [
        {
          awardType: 'origin-awarded',
          dateUTC: '2026-05-01T00:00:00Z',
          handle: 'synthetic-author',
          stars: 2,
          title: 'Merit-Based Origin Awarded'
        }
      ]
    }
  },

  // State 3: Material Origin Challenge (Origin Contested, incumbent retained)
  originContested: {
    id: 'synthetic-author/synthetic-origin-contested',
    name: 'Synthetic Origin Contested',
    level: '4★',
    trustMagnitude: 105,
    overallTrustGrade: 'A',
    genericSkillRef: 'synthetic-capability-root',
    trustLifecycle: {
      snapshot: {
        snapshotId: 'snap-synthetic-2026-10-26-003',
        evaluatedAtUTC: '2026-10-26T00:00:00Z',
        policyVersion: 'yggdrasil-4.0.0-synthetic',
        approvedBy: 'synthetic-maintainer',
        approvalRef: 'https://github.com/gaia-research/gaia-skill-tree/pull/9999'
      },
      approvedStanding: {
        status: 'contested',
        approvedStars: 4,
        approvedTm: 105
      },
      origin: {
        status: 'contested',
        currentOriginHandle: 'synthetic-author',
        contested: true,
        genericSkillRef: 'synthetic-capability-root'
      },
      challenges: [
        {
          challengeId: 'ch-synthetic-material-001',
          claimId: 'claim-core-mastery-01',
          claim: 'Core execution engine is superseded by superior open implementation',
          behaviorId: 'core-task-completion',
          materialToOrigin: true, // Material to Origin: causes Origin Contested marker!
          scopeDescription: 'Whole-bucket qualification test on canonical evaluation suite',
          status: 'verified-pending',
          pinnedVersion: 'v1.2.0',
          pinnedSha: 'f6e5d4c3b2a1',
          environment: 'canonical-eval-v1',
          comparator: 'synthetic-challenger/core-skill v3.0',
          baseline: '42% task completion vs 94% challenger',
          verifiedAtUTC: '2026-10-25T14:30:00Z',
          verifier: {
            verifierId: 'synthetic-eval-team',
            verificationMethod: 'canonical-suite-reproduction',
            receiptUrl: 'https://github.com/gaia-research/gaia-skill-tree/issues/9992'
          },
          contributorNoticeRef: 'https://github.com/gaia-research/gaia-skill-tree/issues/9992#notice',
          responseDueUTC: '2026-11-08T14:30:00Z'
        }
      ],
      historicalAwards: [
        {
          awardType: 'origin-awarded',
          dateUTC: '2026-04-10T00:00:00Z',
          handle: 'synthetic-author',
          stars: 4,
          title: 'Merit-Based Origin Awarded'
        }
      ]
    }
  },

  // State 4: Approved Numerical Degradation (Class C adjudicated reduction)
  approvedNumericalDegradation: {
    id: 'synthetic-author/synthetic-degraded',
    name: 'Synthetic Degraded Skill',
    level: '3★',
    trustMagnitude: 72,
    overallTrustGrade: 'B',
    genericSkillRef: 'synthetic-capability-root',
    trustLifecycle: {
      snapshot: {
        snapshotId: 'snap-synthetic-2026-10-26-004',
        evaluatedAtUTC: '2026-10-26T00:00:00Z',
        policyVersion: 'yggdrasil-4.0.0-synthetic',
        approvedBy: 'synthetic-founder',
        approvalRef: 'https://github.com/gaia-research/gaia-skill-tree/pull/9995'
      },
      approvedStanding: {
        status: 'degraded',
        approvedStars: 3,
        approvedTm: 72,
        degradation: {
          priorStars: 4,
          degradedStars: 3,
          reason: 'Independent audit confirmed persistent failure of claimed multi-turn agent coordination',
          decisionRef: 'https://github.com/gaia-research/gaia-skill-tree/issues/9994',
          adjudicatedAtUTC: '2026-10-22T16:00:00Z'
        }
      },
      origin: {
        status: 'held',
        currentOriginHandle: 'synthetic-author',
        contested: false,
        genericSkillRef: 'synthetic-capability-root'
      },
      challenges: [
        {
          challengeId: 'ch-synthetic-upheld-001',
          claim: 'Coordination protocol hangs after 5 turns on agent networks',
          status: 'upheld',
          materialToOrigin: false,
          verifiedAtUTC: '2026-10-10T08:00:00Z',
          verifier: {
            verifierId: 'synthetic-auditor',
            verificationMethod: 'stress-test-suite',
            receiptUrl: 'https://github.com/gaia-research/gaia-skill-tree/issues/9993'
          }
        }
      ],
      historicalAwards: [
        {
          awardType: 'rank-awarded',
          dateUTC: '2026-06-01T00:00:00Z',
          handle: 'synthetic-author',
          stars: 4,
          title: '4★ Extra Promotion'
        }
      ]
    }
  },

  // State 5: Technical Resolution with Recalibration Pending (Class B closed, Class C pending)
  technicalResolutionRecalibrationPending: {
    id: 'synthetic-author/synthetic-recalibration-pending',
    name: 'Synthetic Recalibration Pending',
    level: '3★',
    trustMagnitude: 75,
    overallTrustGrade: 'B',
    genericSkillRef: 'synthetic-capability-root',
    trustLifecycle: {
      snapshot: {
        snapshotId: 'snap-synthetic-2026-10-26-005',
        evaluatedAtUTC: '2026-10-26T00:00:00Z',
        policyVersion: 'yggdrasil-4.0.0-synthetic',
        approvedBy: 'synthetic-maintainer',
        approvalRef: 'https://github.com/gaia-research/gaia-skill-tree/pull/9999'
      },
      approvedStanding: {
        status: 'recalibration-pending',
        approvedStars: 3,
        approvedTm: 75,
        recalibrationPending: {
          reason: 'Class B technical closure passed: upstream patch repaired memory leak under high load. Canonical TM and rank recovery awaiting Class C review.',
          resolvedChallengeId: 'ch-synthetic-resolved-001',
          closedAtUTC: '2026-10-25T18:00:00Z',
          receiptUrl: 'https://github.com/gaia-research/gaia-skill-tree/issues/9996'
        }
      },
      origin: {
        status: 'held',
        currentOriginHandle: 'synthetic-author',
        contested: false,
        genericSkillRef: 'synthetic-capability-root'
      },
      challenges: [
        {
          challengeId: 'ch-synthetic-resolved-001',
          claim: 'Memory leak under sustained 24h worker daemon execution',
          behaviorId: 'daemon-longevity',
          materialToOrigin: false,
          status: 'technically-rebutted',
          pinnedVersion: 'v1.1.0',
          pinnedSha: '112233445566',
          verifiedAtUTC: '2026-10-15T09:00:00Z',
          verifier: {
            verifierId: 'synthetic-tester',
            verificationMethod: 'daemon-memory-profiler',
            receiptUrl: 'https://github.com/gaia-research/gaia-skill-tree/issues/9996#challenge'
          },
          resolution: {
            disposition: 'technically-rebutted',
            resolvedAtUTC: '2026-10-25T18:00:00Z',
            verifierId: 'synthetic-independent-verifier',
            receiptUrl: 'https://github.com/gaia-research/gaia-skill-tree/issues/9996#resolution',
            recalibrationPending: true
          }
        }
      ],
      historicalAwards: []
    }
  },

  // State 6: Upstream-Superseded Historical Challenge (Retained in permanent record)
  upstreamSupersededChallenge: {
    id: 'synthetic-author/synthetic-superseded',
    name: 'Synthetic Upstream Superseded',
    level: '4★',
    trustMagnitude: 140,
    overallTrustGrade: 'A',
    genericSkillRef: 'synthetic-capability-root',
    trustLifecycle: {
      snapshot: {
        snapshotId: 'snap-synthetic-2026-10-26-006',
        evaluatedAtUTC: '2026-10-26T00:00:00Z',
        policyVersion: 'yggdrasil-4.0.0-synthetic',
        approvedBy: 'synthetic-maintainer',
        approvalRef: 'https://github.com/gaia-research/gaia-skill-tree/pull/9999'
      },
      approvedStanding: {
        status: 'in-good-standing',
        approvedStars: 4,
        approvedTm: 140
      },
      origin: {
        status: 'held',
        currentOriginHandle: 'synthetic-author',
        contested: false,
        genericSkillRef: 'synthetic-capability-root'
      },
      challenges: [
        {
          challengeId: 'ch-synthetic-superseded-001',
          claim: 'Older v1.0.0 failed compatibility with Bun runtime',
          behaviorId: 'bun-compat',
          materialToOrigin: false,
          status: 'resolved-by-upstream-improvement',
          pinnedVersion: 'v1.0.0',
          pinnedSha: '998877665544',
          verifiedAtUTC: '2026-07-12T10:00:00Z',
          verifier: {
            verifierId: 'synthetic-bun-verifier',
            verificationMethod: 'runtime-matrix-ci',
            receiptUrl: 'https://github.com/gaia-research/gaia-skill-tree/issues/8881'
          },
          resolution: {
            disposition: 'resolved-by-upstream-improvement',
            resolvedAtUTC: '2026-08-20T11:00:00Z',
            verifierId: 'synthetic-bun-verifier',
            receiptUrl: 'https://github.com/gaia-research/gaia-skill-tree/issues/8881#resolution',
            upstreamVersion: 'v1.5.0',
            upstreamSha: '556677889900'
          }
        }
      ],
      historicalAwards: [
        {
          awardType: 'origin-awarded',
          dateUTC: '2026-06-01T00:00:00Z',
          handle: 'synthetic-author',
          stars: 4,
          title: 'Merit-Based Origin Awarded'
        }
      ]
    }
  },

  // State 7: Partial / Unknown State (no fabrication of zero or false)
  partialUnknownState: {
    id: 'synthetic-author/synthetic-partial',
    name: 'Synthetic Partial Unknown',
    level: '2★',
    trustMagnitude: null,
    overallTrustGrade: null,
    trustLifecycle: {
      snapshot: {
        // Missing snapshotId and evaluatedAtUTC (unpinned)
        policyVersion: 'yggdrasil-4.0.0-synthetic'
      },
      approvedStanding: {
        // Missing approvedStars, missing approvedTm, missing status
      },
      origin: {
        // Missing currentOriginHandle
      }
      // Missing challenges and historicalAwards
    }
  },

  // State 8: Malformed / Shadow / Unverified Allegations (must NOT render as verified)
  malformedAndShadowAllegations: {
    id: 'synthetic-author/synthetic-malformed-allegations',
    name: 'Synthetic Malformed Allegations',
    level: '4★',
    trustMagnitude: 100,
    overallTrustGrade: 'A',
    genericSkillRef: 'synthetic-capability-root',
    // Caller boolean attempts to spoof standing
    isApproved: true,
    hasPassed: true,
    isOriginTransferred: true,
    trustLifecycle: {
      snapshot: {
        snapshotId: 'snap-synthetic-2026-10-26-008',
        evaluatedAtUTC: '2026-10-26T00:00:00Z',
        policyVersion: 'yggdrasil-4.0.0-synthetic'
        // NOTE: Intentionally lacks approvedBy and approvalRef to test P1 provenance gate
      },
      approvedStanding: {
        status: 'in-good-standing',
        approvedStars: 4,
        approvedTm: 100
      },
      origin: {
        currentOriginHandle: 'synthetic-author',
        contested: 'false' // String 'false' must NOT contest Origin (P2)
      },
      challenges: [
        // 1. Shadow proposal (must be filtered out)
        {
          challengeId: 'shadow-001',
          claim: 'Unconfirmed forum rumor regarding latency spike',
          status: 'shadow',
          verifiedAtUTC: '2026-10-25T00:00:00Z',
          verifier: {
            verifierId: 'shadow-agent',
            verificationMethod: 'heuristic',
            receiptUrl: 'https://github.com/gaia-research/gaia-skill-tree/issues/9999'
          }
        },
        // 2. Missing receiptUrl (must be filtered out)
        {
          challengeId: 'no-receipt-002',
          claim: 'Alleged benchmark failure without reproducible link',
          status: 'verified-pending',
          verifiedAtUTC: '2026-10-25T00:00:00Z',
          verifier: {
            verifierId: 'anonymous',
            verificationMethod: 'reproducible-benchmark-runner',
            receiptUrl: ''
          }
        },
        // 3. Model-only verification method (strictly prohibited by doctrine)
        {
          challengeId: 'model-only-003',
          claim: 'LLM self-reported flaw in prompt template',
          status: 'verified-pending',
          verifiedAtUTC: '2026-10-25T00:00:00Z',
          verifier: {
            verifierId: 'llm-evaluator',
            verificationMethod: 'model-only',
            receiptUrl: 'https://github.com/gaia-research/gaia-skill-tree/issues/9998'
          }
        },
        // 4. Non-HTTPS link (javascript: injection attempt)
        {
          challengeId: 'xss-attempt-004',
          claim: 'Link injection attack attempt',
          status: 'verified-pending',
          verifiedAtUTC: '2026-10-25T00:00:00Z',
          verifier: {
            verifierId: 'attacker',
            verificationMethod: 'manual-test',
            receiptUrl: 'javascript:alert(1)'
          }
        }
      ]
    }
  },

  // State 9: Absent trustLifecycle payload (must preserve current UI exactly)
  absentPayload: {
    id: 'synthetic-author/synthetic-no-lifecycle',
    name: 'Synthetic Normal Skill Without Lifecycle',
    level: '3★',
    trustMagnitude: 85,
    overallTrustGrade: 'B',
    genericSkillRef: 'synthetic-capability-root'
    // trustLifecycle is omitted entirely
  },

  // State 10: Contradictory Authority Payload (hero TM 125 vs snapshot approved TM 105)
  contradictoryPayload: {
    id: 'synthetic-author/synthetic-contradictory',
    name: 'Synthetic Contradictory Authority',
    level: '4★',
    trustMagnitude: 125,
    overallTrustGrade: 'A',
    genericSkillRef: 'synthetic-capability-root',
    trustLifecycle: {
      snapshot: {
        snapshotId: 'snap-synthetic-2026-10-26-009',
        evaluatedAtUTC: '2026-10-26T00:00:00Z',
        policyVersion: 'yggdrasil-4.0.0-synthetic',
        approvedBy: 'synthetic-maintainer',
        approvalRef: 'https://github.com/gaia-research/gaia-skill-tree/pull/9999'
      },
      approvedStanding: {
        status: 'in-good-standing',
        approvedStars: 4,
        approvedTm: 105 // Contradicts root hero TM 125!
      },
      origin: {
        status: 'held',
        currentOriginHandle: 'synthetic-author',
        contested: false,
        genericSkillRef: 'synthetic-capability-root'
      },
      challenges: []
    }
  },

  // State 11: Rehearsal Snapshot State (explicitly marked rehearsal)
  rehearsalState: {
    id: 'synthetic-author/synthetic-rehearsal',
    name: 'Synthetic Rehearsal State',
    level: '4★',
    trustMagnitude: 120,
    overallTrustGrade: 'A',
    genericSkillRef: 'synthetic-capability-root',
    trustLifecycle: {
      snapshot: {
        snapshotId: 'snap-rehearsal-2026-10-26-010',
        evaluatedAtUTC: '2026-10-26T00:00:00Z',
        policyVersion: 'yggdrasil-4.0.0-rehearsal',
        approvedBy: 'synthetic-maintainer',
        approvalRef: 'https://github.com/gaia-research/gaia-skill-tree/pull/9999',
        rehearsal: true
      },
      approvedStanding: {
        status: 'in-good-standing',
        approvedStars: 4,
        approvedTm: 120
      },
      origin: {
        status: 'held',
        currentOriginHandle: 'synthetic-author',
        contested: false,
        genericSkillRef: 'synthetic-capability-root'
      },
      challenges: []
    }
  }
};

if (typeof module === 'object' && module.exports) {
  module.exports = SYNTHETIC_FIXTURES;
}
