import numpy as np
import pandas as pd
from math import pow, sqrt
from bs4 import BeautifulSoup
from sklearn.cluster import KMeans


def rgb_mask(k, segmented_image, clusters):
  # clusters: key=rgb_sum --> value=[r, g, b, area]
  color_map = []

  # Find & Replace White
  replace_rgb(250,250,250, clusters, segmented_image, color_map)

  # Find & Replace Black
  replace_rgb(30,30,30, clusters, segmented_image, color_map)

  # Find & Replace Green
  replace_rgb(0,255,0, clusters, segmented_image, color_map)

  # Find & Replace Red
  replace_rgb(255,0,0, clusters, segmented_image, color_map)

  # Find & Replace Blue
  if k > 4:
    replace_rgb(0,0,255, clusters, segmented_image, color_map)

  # Find & Replace 6th color
  if k > 5:
    replace_rgb(255,255,102, clusters, segmented_image, color_map)

  return segmented_image, color_map


def replace_rgb(r, g, b, clusters, data, color_map):
  cluster = find_nearest_cluster(r, g, b, clusters)
  red, green, blue = data[:,:,0], data[:,:,1], data[:,:,2]
  mask = (red == cluster[0]) & (green == cluster[1]) & (blue == cluster[2])
  data[:,:,:3][mask] = [r, g, b]
  color_map.append(cluster + [r, g, b])


def find_nearest_cluster(r, g, b, clusters):
  min_key, min_dist = 0, float('inf')
  for key, color in clusters.items():
    dist = sqrt(pow(r-color[0], 2) + pow(g-color[1], 2) + pow(b-color[2], 2))
    if dist <= min_dist:
      min_dist, min_key = dist, key
  return clusters.pop(min_key)


def K_means(x,y,z,n,plot=False):
  kmeans = KMeans(n_clusters = n)
  df = pd.DataFrame({
    'x':x,
    'y':y,
    'z':z
  })
  kmeans.fit(df)
  labels = kmeans.predict(df)
  centroids = kmeans.cluster_centers_
  return labels, centroids


def K_means_seg(img, n):
  img_resized = np.resize(img, (img.shape[0] * img.shape[1], 3))
  labels, centroids = K_means(img_resized[:, 0],
                              img_resized[:, 1],
                              img_resized[:, 2],
                              n=n, plot=False)

  # Color segmentation
  centroids = np.uint8(centroids) # 0 to 255
  img_seg = centroids[labels]
  img_seg = np.resize(img_seg, (img.shape[0], img.shape[1], 3))
  area_t = labels.size
  stats = {}
  for i in range(n):
    area = (i == labels).sum()
    area_perc = round(area / area_t, 4)
    rgb = centroids[i]
    rgb_sum = sum([rgb[0], rgb[1], rgb[2]])
    stats[rgb_sum] = [rgb[0], rgb[1], rgb[2], area_perc]

  return img_seg, stats


def generate_combined_report(n, image_names, seg_img_names, stats_lists, report_file, template_file):
  with open(template_file, 'r') as fp:
    soup = BeautifulSoup(fp, 'html.parser')
    soup.find('title').string = "combined-k{n}"

    # ids 0, 2, 4 are original images
    for i in range(len(image_names)):
      soup.find('img', id=f'img{i*2}')['src'] = image_names[i]
      soup.find('figcaption', id='fig' + f'{i*2}').string = f'Original'

    # ids 1, 3, 5 are segmented images
    j = 0
    for i in [1, 3, 5]:
      soup.find('img', id=f'img{i}')['src'] = seg_img_names[j]
      soup.find('figcaption', id=f'fig{i}').string = f'Segmented with K-Means; k={n}'
      j += 1

    # go through each area %; for each image, for each color, for each area%
    l = 0
    j = 1
    letters = ['A', 'B', 'C']
    for img_group in stats_lists:
      for stat in img_group:
        # A1, B1, C1
        # A2, B2, C2, etc.
        
        soup.find('td', id=letters[l] + f'{j}').string = str(round(stat[3] * 100, 1))
        j += 1
      j = 1
      l += 1

    with open(report_file, 'wb') as fp:
      fp.write(soup.prettify('utf-8'))