
import logging
import re
from typing import List, Dict, Optional
from config import TARGET_MATCHING, INDUSTRIES, TARGETS
from database.crud import get_all_profiles, get_profiles_by_industry, get_profiles_by_target, get_active_profile, get_all_activity_scores

logger = logging.getLogger(__name__)


async def apply_filters(user_id: int) -> List[Dict]:
    try:
        user_profile = await get_active_profile(user_id)
        
        if not user_profile:
            logger.error(f"apply_filters: активная анкета не найдена для user_id {user_id}")
            return []
        
        user_industry = user_profile.get('industry')
        user_target = user_profile.get('target')
        if not all([user_industry, user_target]):
            logger.error(f"apply_filters: missing required fields in active profile: {user_profile}")
            return []
        
        all_profiles = await get_all_profiles()
        if not all_profiles:
            logger.info("apply_filters: no profiles in database")
            return []
        filtered_profiles = []
        for profile in all_profiles:
            if profile.get('user_id') == user_id:
                continue
            
            target_match = TARGET_MATCHING.get(user_target)
            if not target_match:
                target_match = user_target
            if profile.get('target') != target_match:
                continue
            
            if profile.get('industry') != user_industry:
                continue
            
            filtered_profiles.append(profile)
        activity_scores = await get_all_activity_scores()
        for profile in filtered_profiles:
            profile['activity_score'] = activity_scores.get(profile['user_id'], 0)
        filtered_profiles.sort(key=lambda x: x.get('activity_score', 0), reverse=True)
        
        logger.info(f"apply_filters: filtered {len(filtered_profiles)} profiles for user {user_id} (active profile: {user_profile['name']})")
        return filtered_profiles
        
    except Exception as e:
        logger.error(f"apply_filters error: {e}", exc_info=True)
        return []

async def get_profiles_by_filters(
    industry: Optional[str] = None,
    target: Optional[str] = None,
    exclude_user_id: Optional[int] = None,
    limit: int = 50
) -> List[Dict]:
    try:
        profiles = []
        
        if industry and target:
            industry_profiles = await get_profiles_by_industry(industry)
            profiles = [p for p in industry_profiles if p.get('target') == target]
        elif industry:
            profiles = await get_profiles_by_industry(industry)
        elif target:
            profiles = await get_profiles_by_target(target)
        else:
            profiles = await get_all_profiles()
        
        if exclude_user_id:
            profiles = [p for p in profiles if p.get('user_id') != exclude_user_id]
        
        if limit and len(profiles) > limit:
            profiles = profiles[:limit]
        
        return profiles
        
    except Exception as e:
        logger.error(f"get_profiles_by_filters error: {e}", exc_info=True)
        return []

def calculate_similarity(text1: str, text2: str) -> float:
    try:
        if not text1 or not text2:
            return 0.0
        text1_clean = re.sub(r'[^\w\s]', ' ', text1.lower()).split()
        text2_clean = re.sub(r'[^\w\s]', ' ', text2.lower()).split()

        if not text1_clean or not text2_clean:
            return 0.0
        
        set1 = set(text1_clean)
        set2 = set(text2_clean)
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
        
    except Exception as e:
        logger.error(f"calculate_similarity error: {e}")
        return 0.0

async def rank_profiles_by_relevance(user_profile: Dict, profiles: List[Dict]) -> List[Dict]:
    try:
        if not profiles:
            return []
        
        user_description = user_profile.get('description', '')
        if not user_description:
            import random
            random.shuffle(profiles)
            return profiles
        for profile in profiles:
            profile_description = profile.get('description', '')
            similarity = calculate_similarity(user_description, profile_description)
            profile['similarity_score'] = similarity
        
        profiles.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        
        return profiles
        
    except Exception as e:
        logger.error(f"rank_profiles_by_relevance error: {e}")
        return profiles

async def get_matching_profiles(user_profile: Dict) -> List[Dict]:
    try:
        filtered_profiles = await apply_filters(user_profile)
        
        if not filtered_profiles:
            return []
        ranked_profiles = await rank_profiles_by_relevance(user_profile, filtered_profiles)
        
        return ranked_profiles
        
    except Exception as e:
        logger.error(f"get_matching_profiles error: {e}", exc_info=True)
        return []

def validate_profile_filters(profile: Dict) -> bool:
    try:
        required_fields = ['industry', 'target']
        for field in required_fields:
            if field not in profile:
                logger.error(f"Missing required field: {field}")
                return False
        
        if profile['industry'] not in INDUSTRIES:
            logger.error(f"Invalid industry: {profile['industry']}")
            return False
        
        if profile['target'] not in TARGETS:
            logger.error(f"Invalid target: {profile['target']}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"validate_profile_filters error: {e}")
        return False

async def get_profile_match_score(profile1: Dict, profile2: Dict) -> float:
    try:
        score = 0.0
        target1 = profile1.get('target')
        target2 = profile2.get('target')
        
        if target1 and target2:
            if TARGET_MATCHING.get(target1) == target2:
                score += 0.5 
        if profile1.get('industry') == profile2.get('industry'):
            score += 0.3
        desc1 = profile1.get('description', '')
        desc2 = profile2.get('description', '')

        if desc1 and desc2:
            similarity = calculate_similarity(desc1, desc2)
            score += similarity * 0.2 
        
        return min(score, 1.0)
        
    except Exception as e:
        logger.error(f"get_profile_match_score error: {e}")
        return 0.0

async def apply_filters_simple(user_profile: Dict) -> List[Dict]:
    return await get_matching_profiles(user_profile)


from database.crud import get_user_activity_score, get_all_activity_scores
