#!/usr/bin/Rscript

#####################################
# load all the required packages
#####################################

library(RCurl)
library(wordcloud)
library(RColorBrewer)
library(gplots)
library(lsa)
library(Rgraphviz)
library(tm)
library(slam)

########################################################################
########################################################################

#########################
# define helper functions
#########################

###################################
# function that read volume id list
################################### 
read.vol <- function(volID.path) {
	# volID.path is the path of the volumeIDList file 
	con <- file(volID.path, open = "r")
	idList <- vector()
	
	# number of lines to read at a time    
	numLinesToRead <- 1000

	while(length(input <- readLines(con, n = numLinesToRead)) > 0) {
		for (i in 1 : length(input)) {
			idList <- append(idList, input[i])
        	}
    	}

	# close file
	close(con)
	return(idList)
}

################################
# function that reads zip entry
################################
read.entry <- function(zipFileName, zipEntryName, seperator) {
	
	zipEntry <- unz(zipFileName, zipEntryName)

	entryData <- read.table(zipEntry, sep = seperator, quote = "", blank.lines.skip = TRUE)

	# close file
	unlink(zipEntry)
	return(entryData)
}

###############################################################
# function that converts a sparse matrix to a non-sparse matrix
###############################################################
sparse2nonsparse <- function(sparseMatrix, volIDList, wordList) {

	nonsparseMatrix <- matrix(0, dim(volIDList)[1], dim(wordList)[1], dimnames = list(volIDList[, 1], wordList[, 1]))

	for (i in 1 : dim(sparseMatrix)[1]) {
		nonsparseMatrix[sparseMatrix[i, 1] + 1, sparseMatrix[i, 2] + 1] <- sparseMatrix[i, 3]
	}

	return(nonsparseMatrix)
}

##################################################################
# function that calculates word relevance based on cosine distance
##################################################################
wordrelv <- function(nonSparseMatrix, topNwords) {
	
	if (topNwords > dim(nonSparseMatrix)[2]) {
		print("Specified topNwords exceeds the # of total words in dict.")
		return(1)	
	}

	idx <- order(colSums(nonSparseMatrix), decreasing = TRUE)

	colnames <- colnames(nonSparseMatrix)[idx][1 : topNwords]

	revMatrix <- matrix(0, topNwords, topNwords, dimnames = list(colnames, colnames))

	sortedMatrix <-  nonSparseMatrix[, idx]

	for (i in 1 : topNwords) {
		for (j in 1 : topNwords) {
			revMatrix[i, j] <- cosine(sortedMatrix[, i], sortedMatrix[, j])
		}	
	}

	return(revMatrix)
}

#######################################################
# function that returns sorted matrix by word frequency
#######################################################

sort.matrix <- function(nonSparseMatrix) {

	matrix <- nonSparseMatrix[, order(colSums(nonSparseMatrix), decreasing = TRUE)]
	
	return(matrix)	
}

#################################################################
# function that returns string w/o leading or trailing whitespace
#################################################################
trim <- function (x) gsub("^\\s+|\\s+$", "", x)

########################################################################
########################################################################


#######################################
# Step 1. Read volume id list from file
#######################################

# each line in this txt file is a HathiTrust volume ID
volIDListFile <- "./volIDList.txt"

idList <- read.vol(volIDListFile)

##################################################################
# Step 2. Invoke featureAPI to retrieve Term-document Matrix (TDM)
##################################################################

# form the volume id list parameter in the RESTAPI

# concatenate volume ids with separate '|'
idListPara <- paste(idList, collapse = "|")

# remove leading and trailing whitespaces
idListPara <- trim(idListPara)

#idListPara

# invoke featureAPI

# end point of featureAPI
featureAPIEPR <- "http://chinkapin.pti.indiana.edu:9447/feature-api/tdm"

# http get, this approach works best when the volume id list is short
#zipBinary <- getBinaryURL("http://chinkapin.pti.indiana.edu:9447/feature-api/tdm?volumeIDs=mdp.39015065582069|mdp.39015065120993&dict=true")

# http post
zipBinary <- postForm(featureAPIEPR, .params = c(volumeIDs=idListPara, dict="true"), style = "post", binary = TRUE)

# store the returned zip file locally
zipFileName <- "tdm.zip"
writeBin(as.vector(zipBinary), zipFileName)

# three entries within the returned zip file
dictFileName <- "dictionary"
tdmFileName <- "tdm"
volumeIDsFileName <- "volumeIDs"

# read volume id list file
volIDList <- read.entry(zipFileName, volumeIDsFileName, ",")

#volIDList[1 : 5, 1 : 2]

# read word list file
wordList <- read.entry(zipFileName, dictFileName, "\t")

#wordList[1 : 5, 1 : 2]

# read tdm matrix
sparseTDM <- read.entry(zipFileName, tdmFileName, ",")
#sparseTDM[1 : 5, 1 : 3]

sparseTDM <- as.matrix(sparseTDM, dimnames = NULL)
#sparseTDM[1 : 5, 1 : 3]

#################################################
# Step 3. Convert sparse matrix to non-sparse one
#################################################
nonsparseTDM <- sparse2nonsparse(sparseTDM, volIDList, wordList)

#nonsparseTDM[1 : 2, 1 : 5]

##################################################
# Step 4. Derive info from TDM and do visulization
##################################################

# get word counts in decreasing order
wordFreqs <- sort(colSums(nonsparseTDM), decreasing = TRUE) 

#wordFreqs[1 : 10]
#names(wordFreqs)[1 : 10]

# set TRUE if only display top N words, otherwise FALSE
displayTopN <- TRUE

# create a data frame with words and their frequencies

if (displayTopN) {
	# you can contral the top # of words here
	topN <- 500
	dm <- data.frame(word = names(wordFreqs)[1 : topN], freq = wordFreqs[1 : topN])
} else {
	dm <- data.frame(word = names(wordFreqs), freq = wordFreqs)
}

# set pdf as device, all below plots go to "Rplots.pdf" file
if(dev.cur() == 1) pdf()
dev.cur()

#####################
# plot the wordcloud
#####################
wordcloud(dm$word, dm$freq, random.order = FALSE, colors = brewer.pal(8, "Dark2"))

###############################
# plot frequency of top N words
###############################
numTopWords <- 10

#names(wordFreqs)[1 : numTopWords]

topWords <- head(wordFreqs, numTopWords)

x <- barplot(topWords, xaxt="n")
text(cex = 1, x = x -.25, y = -50, names(topWords), xpd = TRUE, srt = 45)

##################################
# plot word frequency distribution
##################################

# normalize by # of documents
wordFreqs <- wordFreqs / dim(nonsparseTDM)[1]

numBins <- 200
hist(wordFreqs[wordFreqs > 20], breaks = numBins, xlab = "Frequency", ylab = "# of words", main = "Word frequency distribution")

#######################################
# plot heatmap of word relevance matrix
#######################################

topNwords <- 30
revMatrix <- wordrelv(nonsparseTDM, topNwords)
heatmap.2(revMatrix, dendrogram='none', trace = "none")

#######################################
# plot PCA
#######################################

# sort matrix
sortedMatrix <- sort.matrix(nonsparseTDM)

firstNumWords <- 100

# get a small matrix, with first "firstNumWords" terms in the matrix
small <- sortedMatrix[, 1 : firstNumWords]

# run PCA, remember to perform transpose first
pca <- prcomp(t(small))

# draw plot
plot(pca$x[, 1], pca$x[, 2], xlab = "", ylab = "")
text(pca$x[, 1], pca$x[, 2], row.names(pca$x), cex = 0.6, pos = 4, col = "red")

#######################################
# visualize using Rgraphviz package
#######################################

#random plot N terms

numRandTerms <- 20

dtm <- as.simple_triplet_matrix(nonsparseTDM)

dtm <- as.DocumentTermMatrix(dtm, weighting = weightTf)

plot(dtm, terms = Terms(dtm)[1 : numRandTerms], corThreshold = 0.2, weighting = FALSE)

#######################################
# inspect a paticular word
#######################################

#wordIdx <- 50
#termFreqs <- inspect(dtm[, wordIdx])[,1]

#hist(termFreqs, main="word frequency", xlab="frequency")

