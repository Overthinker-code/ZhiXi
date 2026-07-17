import assert from 'node:assert/strict';
import {
  isRecommendationPreviewCurrent,
  shouldPrepareRecommendation,
} from '../src/components/resource/recommendationPreviewSession';

assert.equal(shouldPrepareRecommendation(null, 'recommendation-1'), true);
assert.equal(
  shouldPrepareRecommendation('recommendation-1', 'recommendation-1'),
  false,
  'a refreshed object with the same recommendation id must not issue another preview request'
);
assert.equal(shouldPrepareRecommendation('recommendation-1', 'recommendation-2'), true);
assert.equal(shouldPrepareRecommendation('recommendation-1', null), false);

assert.equal(isRecommendationPreviewCurrent(4, 4, 'recommendation-1', 'recommendation-1'), true);
assert.equal(
  isRecommendationPreviewCurrent(5, 4, 'recommendation-1', 'recommendation-1'),
  false,
  'a newer request invalidates an older response'
);
assert.equal(
  isRecommendationPreviewCurrent(4, 4, null, 'recommendation-1'),
  false,
  'closing the dialog prevents an in-flight response from updating preview state'
);

console.log('recommendation preview session tests passed');
