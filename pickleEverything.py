import sys
# sys.path.insert(0, '/Library/Python/2.7/site-packages/')
import pickle,json, collections, operator, re, string
from util import User, Biz, Review, Recommender
import pandas as pd
from gensim.models import Doc2Vec
from nltk.corpus import stopwords
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer

# sys.setrecursionlimit(1500)

remove_punctuation_map = dict((ord(char), None) for char in string.punctuation)
remove_punctuation_map.pop(ord('\''), None)
stopwordsEng = stopwords.words('english')
removeStopWordsMap = dict((stopWord, None) for stopWord in stopwordsEng)

def tokenize(text):
    text = text.translate(remove_punctuation_map).lower()
    tokens = re.findall(r"[\w\u0027]+", text)
    tokens = [word for word in tokens if word not in stopwords.words('english')]
    return tokens

userRead = open('../yelp_academic_dataset_user.json')
minUserReviews = 100
minBizReviews = 100
maxUsers = 40
maxBizs = 40
maxReviewsPerBiz = 20
city = 'Pittsburgh'

# get the maxBizs number of businesses in a city with the highest review count
bizRead = open('../yelp_academic_dataset_business.json')
jsonBizs = []
bizIdToJsonBiz = {}
n = 0
for line in bizRead:
    jsonBiz = json.loads(line)
    if 'Restaurants' in jsonBiz['categories'] and jsonBiz['review_count'] >= minBizReviews and (city == None or city == jsonBiz['city']):
        jsonBizs.append((jsonBiz['review_count'], jsonBiz))
        bizIdToJsonBiz[jsonBiz['business_id']] = jsonBiz
        n += 1
    if n >= maxBizs:
        break
bizRead.close()
jsonBizs.sort(reverse=True)  # now sorted list of businesses (review count, jsonBiz)
print "N bizs in city: {}".format(len(jsonBizs))
jsonBizs = jsonBizs[:maxBizs]
print "N reviews for least popular of the popular bizs: {}".format(jsonBizs[-1][0])
jsonBizs = [biz for _, biz in jsonBizs]


#get all the reviews for the extracted businesses and keep count of the most popular userIds
reviewsRead = open('../yelp_academic_dataset_review.json')
jsonReviews = []
userIdsToReviewCount = collections.Counter()
bizIds = bizIdToJsonBiz.keys()
# bizIdToReviewCount = dict.fromkeys(bizIds, 0)
reviewIds = set()
for line in reviewsRead:
    jsonReview = json.loads(line)
    if jsonReview['business_id'] in bizIds and (jsonReview['user_id'] + jsonReview['business_id']) not in reviewIds:
        # if bizToReviewCount[jsonReview['business_id']] <= maxReviewsPerBiz:
        jsonReview["text"] = jsonReview["text"].lower()
        jsonReviews.append(jsonReview)
        userIdsToReviewCount[jsonReview['user_id']] += 1
        reviewIds.add(jsonReview['user_id'] + jsonReview['business_id'])
        # bizToReviewCount[review.bizId] += 1
reviewsRead.close()
userIdsByCount = sorted(userIdsToReviewCount.items(), key=operator.itemgetter(1), reverse=True)
userIdsByCount = userIdsByCount[:maxUsers]

userIds = set()
for userId in userIdsByCount:
    userIds.add(userId[0])
    print userId

#get all the users that wrote the reviews above for the businesses above
users = []
userIdToUser = {}
# n = 0
for line in userRead:
    jsonUser = json.loads(line)
    if jsonUser['user_id'] in userIds:
        user = User(jsonUser)
        users.append(user)
        userIdToUser[user.id] = user
        # n += 1
        # if n >= maxUsers:
        #     break
userRead.close()

bizs = []
bizIdToBiz = {}
for jsonBiz in jsonBizs:
    biz = Biz(jsonBiz)
    bizs.append(biz)
    bizIdToBiz[biz.id] = biz

reviews = []
bizIds = bizIdToBiz.keys()
for jsonReview in jsonReviews:
    if jsonReview['user_id'] in userIds and jsonReview['business_id'] in bizIds:
        reviews.append(Review(jsonReview))


# # get all the other reviews for the users in our set that are NOT for the restaurants we have
# userIds = userIdToUser.keys()
# reviewsRead = open('../yelp_academic_dataset_review.json')
# for line in reviewsRead:
#     jsonReview = json.loads(line)
#     if jsonReview['user_id'] in userIds and (jsonReview['user_id'] + jsonReview['business_id']) not in reviewIds:
#         jsonReview["text"] = jsonReview["text"].lower()
#         review = Review(jsonReview)
#         reviews.append(review)
# reviewsRead.close()

reviewIdToIndex = {}
reviewIds = []
reviewCorpus = []



reviewStars = []
for i in xrange(len(reviews)):
    reviewIds.append(reviews[i].getId())
    reviewIdToIndex[reviews[i].getId()] = i
    reviewCorpus.append(reviews[i].getText())
    reviewStars.append(reviews[i].getStars())

# pickle.dump(bizs, open('business_list', 'wb'))
# pickle.dump(users, open('user_list', 'wb'))
# pickle.dump(reviews, open('review_list', 'wb'))

# preprocess corpus to remove stopwords
# processedCorpus = []
# remove_punctuation_map = dict((ord(char), None) for char in string.punctuation)
# remove_punctuation_map.pop(ord('\''), None)
# stopwordsEng = stopwords.words('english')
# removeStopWordsMap = dict((stopWord, None) for stopWord in stopwordsEng)
# for doc in reviewCorpus:
#     newDoc = doc.translate(remove_punctuation_map)
#     newDoc = newDoc.lower()
#     tokens = re.findall(r"[\w\u0027]+", newDoc)
#     tokens = [word for word in tokens if word not in stopwords.words('english')]
#     newDoc = ' '.join(tokens)
#     processedCorpus.append(newDoc)
# reviewCorpus = processedCorpus
#
# pickle.dump(reviewCorpus, open('reviewCorpus', 'wb'))

# data = np.mat([np.transpose(reviewIds), np.transpose(reviewCorpus)])


#data[0, :] is the array of all biz id's
#data[1, :] is the array of all the reviews

model = Doc2Vec.load('doc2VecModel')
# vectorizedReviewTexts = TfidfVectorizer().fit_transform(reviewCorpus)
for i in xrange(len(reviews)):
    text = tokenize(reviews[i].getText())
    reviews[i].setVectorizedText(model.infer_vector(text))
    # reviews[i].setVectorizedText(vectorizedReviewTexts[i])
    reviews[i].setText(None)


#make all the reviews for businesses and users accessible to each other
for review in reviews:
    if review.bizId in bizIds:
        biz = bizIdToBiz[review.bizId]
        biz.addReview(review)
    if review.userId in userIds:
        user = userIdToUser[review.userId]
        user.addReview(review)


#filter for users with a minimum number of reviews in our list of reviews (different from their reviewCount field)
# usersWithManyReviews = []
# for user in users:
#     if len(user.reviews) >= 20:
#         usersWithManyReviews.append(user)

for user in users:
    user.combineDoc2VecVectorizedReviews()
#     # user.combineTfidfVectorizedReviews()
for biz in bizs:
    biz.combineDoc2VecVectorizedReviews()
#     # biz.combineTfidfVectorizedReviews()

recommender = Recommender(users, bizs, reviews)
print len(users)
print len(bizs)
print len(reviews)
pickle.dump(recommender, open('pickledRecommender', 'wb'))

# pickle.dump(bizs, open('business_list', 'wb'))
# pickle.dump(usersWithManyReviews, open('user_list', 'wb'))
# pickle.dump(reviews, open('review_list', 'wb'))
# pickle.dump(bizIdToReviews, open('biz_id_to_review', 'wb'))
# pickle.dump(bizIdToText, open('biz_id_to_review_text', 'wb'))
